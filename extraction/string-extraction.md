# Getting the UI strings out of EXAPUNKS.exe

Read this before running `extract_ui.py`, and tell the user what it does: it analyses and
decrypts parts of *their* copy of the program, locally. Their store's terms may prohibit
reverse engineering; it is their decision. Nothing produced here may be published.

## The problem

The menus, task list, editor messages etc. are string literals in `EXAPUNKS.exe`, passed to the
localization lookup `L(text, context)`. To translate them via `Content/strings.csv` we need the
exact English keys. The exe is obfuscated with Eazfuscator.NET: type and member names are
mangled (`#=q…`), and every string literal is encrypted in an embedded resource. Code fetches a
literal through a static decryptor, `string Decrypt(int id)`; a call site looks like
`ldc.i4 <id>; call Decrypt`.

## Finding the pieces by structure

Using Mono.Cecil (no fixed metadata tokens, so other builds work):

- **Decryptor**: the static method `string (int32)` with by far the most call sites
  (≈9,900 in the analysed build).
- **Lookup `L()`**: the static method returning `LocString` with two `string` parameters, most
  call sites (≈590). `LocString` itself is not obfuscated.
- **Call sites**: for each `call L()`, the two arguments are the preceding instructions:
  `ldc.i4 id; call Decrypt` (encrypted literal), `ldstr` (plain literal) or
  `ldsfld String::Empty` (empty context). In the analysed build every context was empty.
- **String-table loader** (only needed for the end-to-end check): the static `void ()` method in
  the same class as `L()` that calls `File.ReadAllText`.

## The decryptor's caller check

Calling the decryptor via reflection from outside returns a constant garbage value (`X0X`) for
every id. Its class initializer looks at the stack frame of whoever triggers it first and
derives a wrong key unless that caller is a method of the game assembly; the key is derived
once and kept.

So the first call has to come from the game's own code. `Extract.cs` picks the shortest
**side-effect-free** game method that begins with `ldc.i4 n; call Decrypt` and invokes it once via
reflection with default arguments. "Side-effect-free" is checked strictly: its class has no
static constructor; it reads no static field except `String.Empty`, writes no field, creates no
object except a `StringBuilder`, uses no function pointers, calls nothing but the decryptor and
`System.String`/`StringBuilder`, and takes only string or primitive parameters. That makes the
decryptor's class initializer run with a game method as caller. After that, the decryptor can
be invoked via reflection for every id and returns real strings. The tool aborts if the results
look like garbage (fewer than 3 distinct values, or less than 90 % of strings mostly printable).

The run happens in a scratch directory (`workspace/run/`) with a copy of the backed-up exe and
the game's own DLLs (not its bundled `mscorlib`/`System*`), under the system Mono.

## Output

`workspace/source/ui_strings.tsv`: `n, english, context, hint` in program order (neighbouring
rows usually belong to one screen; `hint` is the declaring class when its name isn't
obfuscated, e.g. `EditorScreen`), plus the rows of the original `Content/strings.csv`
(engine strings such as histogram labels). Escapes: `\n`, `\t`, `\\`. The analysed build
yields 499 strings (~2,300 words).

## End-to-end check

`verify_ui.py` copies the patched exe, the built `strings.csv` and the game's DLLs into a
scratch directory, initializes the decryptor the same way, sets the localization class's
current-language field to the target language, runs the game's own loader and looks every key up through `L()`.
Expected: everything resolves to the translation except keys with leading/trailing spaces
(the game trims CSV fields, so those can never match).
