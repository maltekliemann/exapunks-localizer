# extraction/ — decrypting the UI strings (separable)

This folder holds everything that depends on **decrypting the string table inside
`EXAPUNKS.exe`**. Nothing else in the repository needs it.

| File | What it is |
|---|---|
| `string-extraction.md` | Prose explanation: how the strings are protected and how the tools read them |
| `Extract.cs` | Mono/C# tool: locates the decryptor and the localization function by structure, decrypts the UI strings; `verify` mode looks every key up through the game's own code |
| `extract_ui.py` | Runs `Extract.cs` on your backed-up exe → `workspace/source/ui_strings.tsv` |
| `verify_ui.py` | End-to-end check of the installed UI translation |

**Why it is separate.** Reading these strings means getting past the obfuscator's string
encryption (including a check designed to stop exactly this kind of outside access). Publishing
a tool, or a description precise enough to rebuild one, may count as distributing a means of
circumvention: in the US under 17 U.S.C. §1201(a)(2)/(b)(1), in the EU under Art. 7(1)(c) of the
Software Directive (Germany: §69f(2) UrhG). That exposure falls mainly on whoever publishes it.
Whether string obfuscation even counts as a protection measure is unsettled; this is not legal
advice.

So there are two ways to publish this repository:

- **With this folder**, in full (accepting the above).
- **Without this folder:** delete `extraction/` entirely. The skill then skips the UI strings;
  dialogue, briefings, WorkHouse and manual work unchanged, menus stay English.

Keeping only `string-extraction.md` is *not* a middle ground: it is a step-by-step recipe that an
agent can turn into the tool again.
