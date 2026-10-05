/* Headless PC Engine frontend for mednafenPceDev.
 * GPLv2+; integrates with Mednafen's libxxx-mode (no SDL dependency).
 */
#include <mednafen/mednafen.h>
#include <mednafen/mednafen-driver.h>
#include <mednafen/debug.h>
#include <mednafen/video/png.h>
#include <mednafen/video/surface.h>
#include <mednafen/netplay-driver.h>
#include <mednafen/state-driver.h>
#include <mednafen/movie-driver.h>

namespace MDFN_IEN_PCE { extern uint64 *PCE_CycleProf; }
#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace Mednafen;

// pceDev frontend hooks normally supplied by the SDL debugger/video driver.
// In headless mode the same framebuffer is reused every frame, so scanline
// preservation needs no explicit copy. Sync flags are consumed but do not
// create frontend breakpoints.
bool DebugHSyncFlag = false;
bool DebugVSyncFlag = false;
void InitScanLine(uint32) { }
bool IsHSYNCBreakPoint() { DebugHSyncFlag = false; return false; }
bool IsVSYNCBreakPoint() { DebugVSyncFlag = false; return false; }

namespace
{
std::atomic<bool> g_exit(false);
std::vector<uint64_t> g_cov(65536);
uint64_t g_cov_total = 0;

struct HeadlessState
{
 std::unique_ptr<MDFN_Surface> surface;
 std::vector<int32> line_widths;
 MDFN_Rect last_rect = {0, 0, 0, 0};
 uint64_t frame_count = 0;
 uint64_t audio_samples = 0, audio_nonzero = 0;
 unsigned audio_peak = 0;
 bool capture_audio = false;
 std::vector<int16> captured_audio;
 std::vector<int16> audio_buffer = std::vector<int16>(8192);
 std::ofstream y4m;
 int y4m_w = 0;
 int y4m_h = 0;
 bool y4m_active = false;
};

HeadlessState* g_state = nullptr;
// PCE pad data: I, II, Select, Run, Up, Right, Down, Left, then III-VI.
static uint8* g_pad_data = nullptr;

static std::string JsonEscape(const std::string& s)
{
 std::ostringstream o;
 for(unsigned char c : s)
 {
  switch(c)
  {
   case '"': o << "\\\""; break;
   case '\\': o << "\\\\"; break;
   case '\b': o << "\\b"; break;
   case '\f': o << "\\f"; break;
   case '\n': o << "\\n"; break;
   case '\r': o << "\\r"; break;
   case '\t': o << "\\t"; break;
   default:
    if(c < 0x20)
     o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << (unsigned)c << std::dec;
    else
     o << (char)c;
  }
 }
 return o.str();
}

static std::string PercentDecode(const std::string& s)
{
 std::string out;
 out.reserve(s.size());
 for(size_t i = 0; i < s.size(); i++)
 {
  if(s[i] == '%' && i + 2 < s.size())
  {
   char* ep = nullptr;
   const std::string hh = s.substr(i + 1, 2);
   long v = strtol(hh.c_str(), &ep, 16);
   if(ep && *ep == 0)
   {
    out.push_back((char)v);
    i += 2;
    continue;
   }
  }
  if(s[i] == '+') out.push_back(' '); else out.push_back(s[i]);
 }
 return out;
}

static uint32 ParseU32(const std::string& s)
{
 char* ep = nullptr;
 errno = 0;
 unsigned long v = strtoul(s.c_str(), &ep, 0);
 if(errno || !ep || *ep || v > 0xFFFFFFFFUL)
  throw std::runtime_error("invalid integer: " + s);
 return (uint32)v;
}

static int ParseInt(const std::string& s)
{
 char* ep = nullptr;
 errno = 0;
 long v = strtol(s.c_str(), &ep, 0);
 if(errno || !ep || *ep || v < 0 || v > 100000000L)
  throw std::runtime_error("invalid integer: " + s);
 return (int)v;
}

static std::vector<uint64_t> g_prof(1 << 21);
static void CoverageCPUCallback(uint32 pc, bool)
{
 pc &= 0xFFFF;
 static const bool trace_bios = getenv("PCE_TRACE_BIOS") != nullptr;
 if(trace_bios && (pc == 0xEC05 || pc == 0xEB8F))
 {
  std::cerr << "BIOS " << std::hex << pc << " args";
  for(unsigned i = 0; i < 8; i++)
   std::cerr << " " << MDFNGameInfo->Debugger->MemPeek(0x20F8 + i, 1, true, true);
  std::cerr << std::dec << '\n';
 }
 g_cov[pc]++;
 g_cov_total++;
}

static void CoverageEnable(bool enable)
{
#ifdef WANT_DEBUGGER
 if(MDFNGameInfo && MDFNGameInfo->Debugger && MDFNGameInfo->Debugger->SetCPUCallback)
  MDFNGameInfo->Debugger->SetCPUCallback(enable ? CoverageCPUCallback : nullptr, enable);
#else
 (void)enable;
#endif
}

static void CoverageClear()
{
 std::fill(g_cov.begin(), g_cov.end(), 0);
 g_cov_total = 0;
}

static size_t CoverageUnique()
{
 size_t n = 0;
 for(uint64_t v : g_cov) n += !!v;
 return n;
}

static std::vector<std::string> Disassemble(uint32 address, unsigned count)
{
 std::vector<std::string> ret;
#ifdef WANT_DEBUGGER
 if(!MDFNGameInfo || !MDFNGameInfo->Debugger || !MDFNGameInfo->Debugger->Disassemble)
  throw std::runtime_error("debugger/disassembler unavailable");

 uint32 a = address & 0xFFFF;
 for(unsigned i = 0; i < count; i++)
 {
  const uint32 before = a;
  char text[256] = {};
  MDFNGameInfo->Debugger->Disassemble(a, ~0U, text);
  std::ostringstream line;
  line << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << before << "  " << text;
  ret.push_back(line.str());
  if((a & 0xFFFF) == (before & 0xFFFF)) break;
  a &= 0xFFFF;
 }
#else
 (void)address; (void)count;
 throw std::runtime_error("built without debugger support");
#endif
 return ret;
}

static std::vector<uint8_t> MemRead(uint32 address, unsigned length, bool logical)
{
 std::vector<uint8_t> ret(length);
#ifdef WANT_DEBUGGER
 if(!MDFNGameInfo || !MDFNGameInfo->Debugger || !MDFNGameInfo->Debugger->MemPeek)
  throw std::runtime_error("debugger memory peek unavailable");
 for(unsigned i = 0; i < length; i++)
  ret[i] = (uint8_t)MDFNGameInfo->Debugger->MemPeek(address + i, 1, true, logical);
#else
 (void)address; (void)logical;
 throw std::runtime_error("built without debugger support");
#endif
 return ret;
}

static void SaveCoverage(const std::string& path)
{
 std::ofstream f(path.c_str(), std::ios::binary | std::ios::trunc);
 if(!f) throw std::runtime_error("could not open coverage output: " + path);
 f << "{\n  \"format\": \"mednafen-pce-logical-pc-coverage-v1\",\n";
 f << "  \"frames\": " << (g_state ? g_state->frame_count : 0) << ",\n";
 f << "  \"total_instructions\": " << g_cov_total << ",\n";
 f << "  \"unique_logical_pcs\": " << CoverageUnique() << ",\n";
 f << "  \"executed\": [\n";
 bool first = true;
 for(unsigned pc = 0; pc < 65536; pc++)
 {
  if(!g_cov[pc]) continue;
  if(!first) f << ",\n";
  first = false;
  f << "    {\"pc\": \"0x" << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << pc
    << std::dec << "\", \"hits\": " << g_cov[pc] << "}";
 }
 f << "\n  ]\n}\n";
 if(!f) throw std::runtime_error("failed writing coverage output: " + path);
}

static void SaveScreenshot(const std::string& path)
{
 if(!g_state || !g_state->surface || !g_state->last_rect.w || !g_state->last_rect.h)
  throw std::runtime_error("no rendered frame available");
 PNGWrite png(path, g_state->surface.get(), g_state->last_rect, g_state->line_widths.data());
}

static inline uint8_t ClampByte(int v)
{
 return (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
}

static void SampleRGB(int tx, int ty, int tw, int th, int& r, int& g, int& b)
{
 const MDFN_Rect& rect = g_state->last_rect;
 int sy = rect.y + std::min(rect.h - 1, (ty * rect.h) / th);
 int lw = rect.w;
 if(!g_state->line_widths.empty() && g_state->line_widths[0] != ~0)
  lw = g_state->line_widths[sy];
 if(lw <= 0) { r = g = b = 0; return; }
 int sx = rect.x + std::min(lw - 1, (tx * lw) / tw);
 const uint32 pix = g_state->surface->pixels[sy * g_state->surface->pitchinpix + sx];
 g_state->surface->format.DecodeColor(pix, r, g, b);
}

static void Y4MWriteFrame()
{
 if(!g_state || !g_state->y4m_active) return;
 if(!g_state->last_rect.w || !g_state->last_rect.h) return;

 const int w = g_state->y4m_w;
 const int h = g_state->y4m_h;
 std::vector<uint8_t> y((size_t)w * h), u((size_t)w * h), v((size_t)w * h);
 for(int py = 0; py < h; py++)
 {
  for(int px = 0; px < w; px++)
  {
   int r, g, b;
   SampleRGB(px, py, w, h, r, g, b);
   const size_t o = (size_t)py * w + px;
   y[o] = ClampByte((77 * r + 150 * g + 29 * b + 128) >> 8);
   u[o] = ClampByte(((-43 * r - 85 * g + 128 * b + 128) >> 8) + 128);
   v[o] = ClampByte(((128 * r - 107 * g - 21 * b + 128) >> 8) + 128);
  }
 }
 g_state->y4m << "FRAME\n";
 g_state->y4m.write((const char*)y.data(), y.size());
 g_state->y4m.write((const char*)u.data(), u.size());
 g_state->y4m.write((const char*)v.data(), v.size());
 if(!g_state->y4m) throw std::runtime_error("failed writing Y4M frame");
}

static void Y4MStart(const std::string& path)
{
 if(!g_state) throw std::runtime_error("emulator state unavailable");
 if(g_state->y4m_active)
 {
  g_state->y4m.close();
  g_state->y4m_active = false;
 }
 g_state->y4m_w = MDFNGameInfo->nominal_width > 0 ? MDFNGameInfo->nominal_width : 320;
 g_state->y4m_h = MDFNGameInfo->nominal_height > 0 ? MDFNGameInfo->nominal_height : 232;
 g_state->y4m.open(path.c_str(), std::ios::binary | std::ios::trunc);
 if(!g_state->y4m) throw std::runtime_error("could not open Y4M output: " + path);
 uint64_t fps_num = MDFNGameInfo->fps ? MDFNGameInfo->fps : (uint64_t)60 * 16777216ULL;
 uint64_t fps_den = 16777216ULL;
 auto gcd = [](uint64_t a, uint64_t b) { while(b) { uint64_t t = a % b; a = b; b = t; } return a; };
 uint64_t d = gcd(fps_num, fps_den); fps_num /= d; fps_den /= d;
 g_state->y4m << "YUV4MPEG2 W" << g_state->y4m_w << " H" << g_state->y4m_h
              << " F" << fps_num << ":" << fps_den << " Ip A1:1 C444\n";
 g_state->y4m_active = true;
}

static void Y4MStop()
{
 if(g_state && g_state->y4m_active)
 {
  g_state->y4m.flush();
  g_state->y4m.close();
  g_state->y4m_active = false;
 }
}

static void RunFrames(unsigned count)
{
 if(!g_state || !g_state->surface) throw std::runtime_error("game not loaded");
 for(unsigned i = 0; i < count && !g_exit.load(); i++)
 {
  std::fill(g_state->line_widths.begin(), g_state->line_widths.end(), ~0);
  EmulateSpecStruct espec;
  espec.surface = g_state->surface.get();
  espec.LineWidths = g_state->line_widths.data();
  espec.skip = false;
  espec.SoundRate = 44100;
  espec.SoundBuf = g_state->audio_buffer.data();
  espec.SoundBufMaxSize = g_state->audio_buffer.size() / 2;
  espec.SoundVolume = 1.0;
  espec.soundmultiplier = 1.0;
  MDFNI_Emulate(&espec);
  for(int32 s = 0; s < espec.SoundBufSize * 2; ++s)
  {
   int sample = espec.SoundBuf[s];
   g_state->audio_samples++;
   if(sample) g_state->audio_nonzero++;
   g_state->audio_peak = std::max(g_state->audio_peak, (unsigned)std::abs(sample));
  }
  if(g_state->capture_audio)
   g_state->captured_audio.insert(g_state->captured_audio.end(), espec.SoundBuf, espec.SoundBuf + espec.SoundBufSize * 2);
  g_state->last_rect = espec.DisplayRect;
  g_state->frame_count++;
  Y4MWriteFrame();
 }
}

static std::string HexBytes(const std::vector<uint8_t>& b)
{
 static const char* h = "0123456789ABCDEF";
 std::string out; out.reserve(b.size() * 2);
 for(uint8_t x : b) { out.push_back(h[x >> 4]); out.push_back(h[x & 15]); }
 return out;
}

static std::vector<std::string> SplitTabs(const std::string& line)
{
 std::vector<std::string> v;
 size_t p = 0;
 while(true)
 {
  size_t n = line.find('\t', p);
  if(n == std::string::npos) { v.push_back(line.substr(p)); break; }
  v.push_back(line.substr(p, n - p)); p = n + 1;
 }
 return v;
}

static void RPCReplyOK(const std::string& extra = "")
{
 std::cout << "{\"ok\":true" << extra << "}\n" << std::flush;
}

static void RPCLoop()
{
 std::string line;
 while(!g_exit.load() && std::getline(std::cin, line))
 {
  try
  {
   std::vector<std::string> a = SplitTabs(line);
   const std::string op = a.empty() ? "" : a[0];
   if(op == "run")
   {
    if(a.size() != 2) throw std::runtime_error("run requires frame count");
    RunFrames(ParseInt(a[1]));
    RPCReplyOK(",\"frame\":" + std::to_string(g_state->frame_count));
   }
   else if(op == "input")
   {
    if(a.size() != 2 || !g_pad_data) throw std::runtime_error("input requires a PCE pad bitmask");
    uint32 mask = ParseU32(a[1]);
    if(mask > 0xFFF) throw std::runtime_error("PCE pad mask exceeds 12 buttons");
    g_pad_data[0] = mask; g_pad_data[1] = mask >> 8;
    RPCReplyOK();
   }
   else if(op == "disasm")
   {
    if(a.size() != 3) throw std::runtime_error("disasm requires address and count");
    auto lines = Disassemble(ParseU32(a[1]), (unsigned)ParseInt(a[2]));
    std::ostringstream o; o << ",\"lines\":[";
    for(size_t i = 0; i < lines.size(); i++) { if(i) o << ','; o << '"' << JsonEscape(lines[i]) << '"'; }
    o << ']'; RPCReplyOK(o.str());
   }
   else if(op == "memread")
   {
    if(a.size() != 4) throw std::runtime_error("memread requires address, length, logical");
    unsigned len = (unsigned)std::min(65536, ParseInt(a[2]));
    auto data = MemRead(ParseU32(a[1]), len, ParseInt(a[3]) != 0);
    RPCReplyOK(",\"hex\":\"" + HexBytes(data) + "\"");
   }
   else if(op == "loadstate")
   {
    if(a.size() != 2) throw std::runtime_error("loadstate requires path");
    std::string p = PercentDecode(a[1]);
    if(!MDFNI_LoadState(p.c_str(), nullptr)) throw std::runtime_error("loadstate failed");
    RPCReplyOK();
   }
   else if(op == "screenshot")
   {
    if(a.size() != 2) throw std::runtime_error("screenshot requires path");
    std::string p = PercentDecode(a[1]); SaveScreenshot(p);
    RPCReplyOK(",\"path\":\"" + JsonEscape(p) + "\"");
   }
   else if(op == "asread")
   {
    if(a.size() != 4) throw std::runtime_error("asread requires space, address, length");
    bool found = false;
    for(const auto& space : *MDFNGameInfo->Debugger->AddressSpaces)
     if(space.name == a[1])
     {
      std::vector<uint8_t> data(std::min(65536, ParseInt(a[3])));
      space.GetAddressSpaceBytes(space.name.c_str(), ParseU32(a[2]), data.size(), data.data());
      RPCReplyOK(",\"hex\":\"" + HexBytes(data) + "\""); found = true; break;
     }
    if(!found) throw std::runtime_error("unknown address space");
   }
   else if(op == "aswrite")
   {
    if(a.size() != 4 || a[3].size() % 2) throw std::runtime_error("aswrite requires space, address, hex bytes");
    std::vector<uint8_t> data;
    for(size_t i = 0; i < a[3].size(); i += 2)
    {
     const std::string pair = a[3].substr(i, 2);
     if(pair.find_first_not_of("0123456789abcdefABCDEF") != std::string::npos)
      throw std::runtime_error("invalid hex byte");
     data.push_back(static_cast<uint8_t>(std::stoul(pair, nullptr, 16)));
    }
    if(data.size() > 65536) throw std::runtime_error("aswrite exceeds 65536 bytes");
    bool found = false;
    for(const auto& space : *MDFNGameInfo->Debugger->AddressSpaces)
     if(space.name == a[1] && space.PutAddressSpaceBytes)
     {
      space.PutAddressSpaceBytes(space.name.c_str(), ParseU32(a[2]), data.size(), 1, true, data.data());
      RPCReplyOK(); found = true; break;
     }
    if(!found) throw std::runtime_error("unknown or read-only address space");
   }
   else if(op == "register_set")
   {
    if(a.size() != 3) throw std::runtime_error("register_set requires name, value");
    bool found = false;
    for(const auto* group : *MDFNGameInfo->Debugger->RegGroups)
     for(const RegType* reg = group->Regs; reg->bsize; ++reg)
      if(reg->bsize != 0xFFFF && a[1] == reg->name && group->SetRegister)
      { group->SetRegister(reg->id, ParseU32(a[2])); found = true; }
    if(!found) throw std::runtime_error("unknown or read-only register");
    RPCReplyOK();
   }
   else if(op == "registers")
   {
    std::ostringstream out; out << ",\"registers\":{";
    bool first = true;
    for(const auto* group : *MDFNGameInfo->Debugger->RegGroups)
     for(const RegType* reg = group->Regs; reg->bsize; ++reg)
      if(reg->bsize != 0xFFFF)
      {
       if(!first) out << ','; first = false;
       out << '"' << reg->name << "\":" << group->GetRegister(reg->id, nullptr, 0);
      }
    out << '}'; RPCReplyOK(out.str());
   }
   else if(op == "record_start")
   {
    if(a.size() != 2) throw std::runtime_error("record_start requires path");
    std::string p = PercentDecode(a[1]); Y4MStart(p);
    RPCReplyOK(",\"path\":\"" + JsonEscape(p) + "\"");
   }
   else if(op == "record_stop") { Y4MStop(); RPCReplyOK(); }
   else if(op == "prof_start") { std::fill(g_prof.begin(), g_prof.end(), 0); MDFN_IEN_PCE::PCE_CycleProf = g_prof.data(); RPCReplyOK(); }
   else if(op == "prof_dump")
   {
    if(a.size() != 2) throw std::runtime_error("prof_dump requires path");
    MDFN_IEN_PCE::PCE_CycleProf = nullptr;
    std::ofstream f(PercentDecode(a[1]));
    for(unsigned i = 0; i < g_prof.size(); i++) if(g_prof[i]) f << std::hex << i << ' ' << std::dec << g_prof[i] << '\n';
    RPCReplyOK();
   }
   else if(op == "cov_clear") { CoverageClear(); RPCReplyOK(); }
   else if(op == "cov_dump")
   {
    if(a.size() != 2) throw std::runtime_error("cov_dump requires path");
    std::string p = PercentDecode(a[1]); SaveCoverage(p);
    RPCReplyOK(",\"path\":\"" + JsonEscape(p) + "\",\"unique_pcs\":" + std::to_string(CoverageUnique()) + ",\"instructions\":" + std::to_string(g_cov_total));
   }
   else if(op == "sound_capture")
   {
    if(a.size() != 3) throw std::runtime_error("sound_capture requires frames, WAV path");
    unsigned frames = ParseU32(a[1]);
    if(frames > 3600) throw std::runtime_error("audio capture limited to 3600 frames");
    g_state->captured_audio.clear(); g_state->capture_audio = true;
    RunFrames(frames); g_state->capture_audio = false;
    std::string path = PercentDecode(a[2]); std::ofstream wav(path, std::ios::binary);
    if(!wav) throw std::runtime_error("cannot open WAV output");
    auto word = [&](uint32_t v, int bytes) { while(bytes--) { wav.put(v & 255); v >>= 8; } };
    uint32_t bytes = g_state->captured_audio.size() * 2;
    wav.write("RIFF",4); word(bytes+36,4); wav.write("WAVEfmt ",8);
    word(16,4); word(1,2); word(2,2); word(44100,4); word(176400,4); word(4,2); word(16,2);
    wav.write("data",4); word(bytes,4);
    for(int16 v : g_state->captured_audio) word((uint16_t)v,2);
    if(!wav) throw std::runtime_error("WAV output failed");
    RPCReplyOK(",\"samples\":" + std::to_string(g_state->captured_audio.size()));
   }
   else if(op == "sound_status")
   {
    RPCReplyOK(",\"samples\":" + std::to_string(g_state->audio_samples) +
               ",\"nonzero\":" + std::to_string(g_state->audio_nonzero) +
               ",\"peak\":" + std::to_string(g_state->audio_peak));
   }
   else if(op == "reset") { MDFNI_Reset(); RPCReplyOK(); }
   else if(op == "status")
   {
    std::ostringstream o;
    o << ",\"frame\":" << g_state->frame_count << ",\"unique_pcs\":" << CoverageUnique()
      << ",\"instructions\":" << g_cov_total << ",\"recording\":" << (g_state->y4m_active ? "true" : "false")
      << ",\"display\":{\"x\":" << g_state->last_rect.x << ",\"y\":" << g_state->last_rect.y
      << ",\"w\":" << g_state->last_rect.w << ",\"h\":" << g_state->last_rect.h << "}";
    RPCReplyOK(o.str());
   }
   else if(op == "quit") { RPCReplyOK(); break; }
   else throw std::runtime_error("unknown rpc command");
  }
  catch(const std::exception& e)
  {
   std::cout << "{\"ok\":false,\"error\":\"" << JsonEscape(e.what()) << "\"}\n" << std::flush;
  }
 }
}

struct Options
{
 std::string rom;
 std::string base_dir = ".mednafen-headless";
 std::string bios;
 std::string screenshot;
 std::string y4m;
 std::string cov;
 uint32 disasm_addr = 0;
 unsigned disasm_count = 0;
 unsigned frames = 1;
 bool rpc = false;
};

static void Usage(const char* argv0)
{
 std::cout
  << "Usage: " << argv0 << " --rom FILE [options]\n"
  << "  --frames N              Run N frames (default 1)\n"
  << "  --disasm ADDR[:COUNT]   Disassemble logical HuC6280 addresses\n"
  << "  --cov FILE.json         Write logical-PC execution coverage\n"
  << "  --screenshot FILE.png   Save the last rendered frame\n"
  << "  --y4m FILE.y4m          Record all run frames as YUV4MPEG2 C444\n"
  << "  --bios FILE             Set pce.cdbios (for CD images)\n"
  << "  --base-dir DIR          Save/config base directory\n"
  << "  --rpc                    Read tab-delimited control commands on stdin\n"
  << "  --help                   Show this help\n";
}

static Options ParseArgs(int argc, char** argv)
{
 Options o;
 for(int i = 1; i < argc; i++)
 {
  std::string a = argv[i];
  auto need = [&](const char* n)->std::string { if(i + 1 >= argc) throw std::runtime_error(std::string(n) + " requires a value"); return argv[++i]; };
  if(a == "--rom") o.rom = need("--rom");
  else if(a == "--frames") o.frames = (unsigned)ParseInt(need("--frames"));
  else if(a == "--cov") o.cov = need("--cov");
  else if(a == "--screenshot") o.screenshot = need("--screenshot");
  else if(a == "--y4m") o.y4m = need("--y4m");
  else if(a == "--bios") o.bios = need("--bios");
  else if(a == "--base-dir") o.base_dir = need("--base-dir");
  else if(a == "--rpc") o.rpc = true;
  else if(a == "--disasm")
  {
   std::string v = need("--disasm");
   size_t c = v.find(':');
   o.disasm_addr = ParseU32(c == std::string::npos ? v : v.substr(0, c));
   o.disasm_count = c == std::string::npos ? 16 : (unsigned)ParseInt(v.substr(c + 1));
  }
  else if(a == "--help" || a == "-h") { Usage(argv[0]); exit(0); }
  else if(a.size() && a[0] != '-' && o.rom.empty()) o.rom = a;
  else throw std::runtime_error("unknown option: " + a);
 }
 if(o.rom.empty()) throw std::runtime_error("--rom is required");
 return o;
}

static void SignalHandler(int) { g_exit.store(true); }
}

namespace Mednafen
{
void MDFND_OutputNotice(MDFN_NoticeType, const char* s) noexcept { if(s) std::cerr << s << std::endl; }
void MDFND_OutputInfo(const char* s) noexcept { if(s) std::cerr << s; }
bool MDFND_CheckNeedExit(void) { return g_exit.load(); }
void MDFND_MidSync(EmulateSpecStruct* espec, const unsigned flags)
{
 if(espec)
 {
  if(flags & MIDSYNC_FLAG_SYNC_TIME)
  {
   espec->MasterCycles_DriverProcessed = espec->MasterCycles;
   espec->SoundBufSize_DriverProcessed = espec->SoundBufSize;
  }
 }
}
void MDFND_MediaSetNotification(uint32, uint32, uint32, uint32) { }
void MDFND_SetStateStatus(StateStatusStruct*) noexcept { }
void MDFND_SetMovieStatus(StateStatusStruct*) noexcept { }
void MDFND_NetplaySetHints(bool, bool, uint32) { }
void MDFND_NetplayText(const char* text, bool) { if(text) std::cerr << text << std::endl; }
}

int main(int argc, char** argv)
{
 std::signal(SIGINT, SignalHandler);
 std::signal(SIGTERM, SignalHandler);

 try
 {
  Options opt = ParseArgs(argc, argv);

  if(!MDFNI_Init()) throw std::runtime_error("MDFNI_Init failed");
  if(!MDFNI_InitFinalize(opt.base_dir.c_str())) throw std::runtime_error("MDFNI_InitFinalize failed");
  if(!opt.bios.empty() && !MDFNI_SetSetting("pce.cdbios", opt.bios))
   throw std::runtime_error("failed to set pce.cdbios");

  MDFNGI* gi = MDFNI_LoadGame("pce", &NVFS, opt.rom.c_str());
  if(!gi) throw std::runtime_error("failed to load ROM/game");

  // A headless frontend must apply the media defaults just like rmdui.
  // LoadCD leaves the emulated drive open until the frontend inserts a disc.
  if(gi->RMD)
   for(uint32 d = 0; d < gi->RMD->DrivesDefaults.size(); d++)
   {
    const auto& media = gi->RMD->DrivesDefaults[d];
    if(!MDFNI_SetMedia(d, media.State, media.Media, media.Orientation))
     throw std::runtime_error("failed to apply default removable media");
   }

  // Initialize all PCE input ports to their declared default device.
  for(uint32 p = 0; p < gi->PortInfo.size(); p++)
  {
   uint32 di = 0;
   for(uint32 j = 0; j < gi->PortInfo[p].DeviceInfo.size(); j++)
    if(!strcmp(gi->PortInfo[p].DeviceInfo[j].ShortName, gi->PortInfo[p].DefaultDevice)) { di = j; break; }
   uint8* input_data = MDFNI_SetInput(p, di);
   if(p == 0) g_pad_data = input_data;
  }

  HeadlessState hs;
  hs.surface.reset(new MDFN_Surface(nullptr, gi->fb_width, gi->fb_height, gi->fb_width, MDFN_PixelFormat::ABGR32_8888));
  hs.line_widths.resize(gi->fb_height, ~0);
  g_state = &hs;

  CoverageClear();
  CoverageEnable(true);

  if(!opt.y4m.empty()) Y4MStart(opt.y4m);
  if(opt.frames) RunFrames(opt.frames);

  if(opt.disasm_count)
  {
   for(const auto& l : Disassemble(opt.disasm_addr, opt.disasm_count)) std::cout << l << '\n';
  }
  if(!opt.screenshot.empty()) SaveScreenshot(opt.screenshot);
  if(!opt.cov.empty()) SaveCoverage(opt.cov);

  if(opt.rpc) RPCLoop();

  Y4MStop();
  CoverageEnable(false);
  g_state = nullptr;
  MDFNI_CloseGame();
  MDFNI_Kill();
  return 0;
 }
 catch(const std::exception& e)
 {
  std::cerr << "headless: " << e.what() << std::endl;
  try { Y4MStop(); } catch(...) { }
  if(MDFNGameInfo) { try { CoverageEnable(false); MDFNI_CloseGame(); } catch(...) { } }
  try { MDFNI_Kill(); } catch(...) { }
  return 1;
 }
}
