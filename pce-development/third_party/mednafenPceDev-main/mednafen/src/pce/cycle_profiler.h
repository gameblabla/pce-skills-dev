/* Mednafen PCE headless cycle-profile clock (GPL-2.0-or-later).
 * Attribute *master-clock* timestamp deltas to the previous physical PC.
 * Frame boundaries reset the core timestamp, not the pending instruction.
 */
#ifndef PCE_DEV_CYCLE_PROFILER_H
#define PCE_DEV_CYCLE_PROFILER_H

#include <stdint.h>

namespace MDFN_IEN_PCE
{
struct CycleProfileClock
{
 uint32_t last_pc = 0;
 uint32_t last_timestamp = 0;
 bool primed = false;

 void Reset()
 {
  primed = false;
  last_pc = 0;
  last_timestamp = 0;
 }

 void Instruction(uint64_t* ticks, uint32_t timestamp, uint32_t physical_pc)
 {
  // The first instruction after prof_start anchors the clock. If an
  // unexpected state load rewinds it, do not manufacture a huge delta.
  if(primed && timestamp >= last_timestamp)
   ticks[last_pc] += timestamp - last_timestamp;
  last_pc = physical_pc;
  last_timestamp = timestamp;
  primed = true;
 }

 void FrameEnd(uint64_t* ticks, uint32_t end_timestamp, uint32_t next_timestamp)
 {
  if(!primed)
   return;
  // Pay out the in-flight instruction, including a TIA/TII block move.
  // Keep its physical PC anchored if the instruction spans a frame boundary.
  if(end_timestamp >= last_timestamp)
   ticks[last_pc] += end_timestamp - last_timestamp;
  last_timestamp = next_timestamp;
 }
};
}
#endif
