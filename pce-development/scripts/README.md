# Local LLVM-MOS PCE CD skill evaluation

`eval_local_ai.py` calls an OpenAI-compatible local chat-completions endpoint
and compares fixed evidence prompts with the skill omitted and loaded. The
skill-assisted run receives `SKILL.md` and only the linked relevant references
and examples. No project checkout or prior conversation log is needed.

The default endpoint is `http://127.0.0.1:8080`. The script selects the first
model from `/v1/models`; override endpoint/model with flags or
`LOCAL_AI_BASE_URL` / `LOCAL_AI_MODEL`.

From this skill directory, run:

```sh
python3 scripts/eval_local_ai.py
```

Useful options:

```sh
python3 scripts/eval_local_ai.py --mode both --workers 1
python3 scripts/eval_local_ai.py --case bank-relocation-safety --case multimodal-vague-hud
python3 scripts/eval_local_ai.py --mode skill --output /tmp/pce-skill-review.json
python3 scripts/eval_local_ai.py --base-url http://127.0.0.1:8080 --model MODEL_ID --limit 3
python3 scripts/eval_local_ai.py --case audio-critical-section --repeats 3
```

Image cases load fixtures relative to `eval_cases.json` and send them as
OpenAI-compatible image content together with the source evidence. The API
server/model must accept image inputs. An image rejection means that case did
not evaluate multimodal behavior.

Cases that need arithmetic run the bundled restricted Python calculator and
include its output in the prompt. The bank-relocation case also runs
`bank_space.py` against a generic linker-report fixture and injects its
capacity-only ranking. The model is instructed not to do arithmetic mentally.
Helper output is test fixture evidence, not model-generated evidence.

The runner disables Qwen-style hidden reasoning by default using
`chat_template_kwargs.enable_thinking=false`. Use `--thinking on` to test the
server's default behavior. Empty or truncated answers stop the run rather than
counting as zero.

Reports preserve raw answers and regex/forbidden-term checks. Scores are
heuristic triage signals, not semantic proof. Review every raw answer,
especially LLVM-MOS-only constraints, bank safety, opcode explanations,
image interpretation, and claims about tests. Baseline/skill outputs are
stochastic; use `--repeats` when one sample is noisy. The default report is
written under `/tmp`.

The suite covers bank relocation, LLVM-MOS CD bring-up, CD/Arcade/VRAM
transfers, large animation swaps, sprite admission, audio critical sections,
game archetypes, image-guided HUD placement, headless/MCP/BIOS debugging,
LLVM-MOS SDK bootstrap, and Python arithmetic. It evaluates written answers
and image submission; it does not edit files or run the emulator.
