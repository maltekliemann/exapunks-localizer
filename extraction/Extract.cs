// Lists every UI string the game passes to its localization function, decrypted.
//
//   mono Extract.exe <EXAPUNKS.exe> <out.tsv>
//   mono Extract.exe verify <patched EXAPUNKS.exe> <Language name> <keys.tsv> <out.txt>
//        (end-to-end check: loads ./Content/strings.csv through the game's own loader, selects
//         the language and looks up every key; see verify_ui.py)
//
// Run it in a directory that contains a copy of the exe and the game's own DLLs (see
// extract_ui.py, which prepares that). Everything is located by structure, not by metadata
// tokens, so other builds of the game should work as long as the shapes are the same:
//
//   decryptor : static string f(int32)          -- the method with the most call sites
//   L()       : static LocString f(string,string) -- the localization lookup, most call sites
//   trigger   : the shortest side-effect-free static method (string/primitive parameters only) that
//               starts with { ldc.i4 n; call decryptor; ... } -- that first call is all we need
//
// The decryptor's type initializer inspects the stack frame of its first caller and derives a
// wrong key unless that caller is a method of the game assembly. So we let a trivial game
// method (the trigger) make the first call, then call the decryptor via reflection.
// See string-extraction.md.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Mono.Cecil;
using Mono.Cecil.Cil;

class Extract {
    static IEnumerable<MethodDefinition> AllMethods(ModuleDefinition mod) {
        foreach (var t in mod.GetTypes())
            foreach (var m in t.Methods)
                if (m.HasBody) yield return m;
    }

    // Callee of a call instruction if it is a method defined in this module (no resolving of
    // external references, so missing referenced assemblies can't break the analysis).
    static MethodDefinition Local(Instruction x, ModuleDefinition mod) {
        return (x.OpCode == OpCodes.Call || x.OpCode == OpCodes.Callvirt) && x.Operand is MethodDefinition d
            && d.Module == mod ? d : null;
    }

    // Integer pushed by any form of ldc.i4.
    static bool LdcI4(Instruction x, out int v) {
        var c = x.OpCode.Code;
        if (c == Code.Ldc_I4) { v = (int)x.Operand; return true; }
        if (c == Code.Ldc_I4_S) { v = (sbyte)x.Operand; return true; }
        if (c == Code.Ldc_I4_M1) { v = -1; return true; }
        if (c >= Code.Ldc_I4_0 && c <= Code.Ldc_I4_8) { v = c - Code.Ldc_I4_0; return true; }
        v = 0;
        return false;
    }

    static bool IsStringEmpty(Instruction x) {
        return x.OpCode == OpCodes.Ldsfld && x.Operand is FieldReference f
            && f.FullName == "System.String System.String::Empty";
    }

    // Only touches strings: its type has no static constructor; it calls nothing but the
    // decryptor and System.String/StringBuilder, creates nothing but StringBuilders, reads no
    // static fields (except String.Empty), writes no fields and takes no function pointers.
    // Invoking it can't run other game code, change game state or touch files.
    static bool IsPure(MethodDefinition m, MethodDefinition dec) {
        if (m.DeclaringType.Methods.Any(c => c.IsConstructor && c.IsStatic)) return false;
        foreach (var x in m.Body.Instructions) {
            var c = x.OpCode.Code;
            if (c == Code.Stsfld || c == Code.Stfld || c == Code.Calli
                || c == Code.Ldftn || c == Code.Ldvirtftn || c == Code.Ldsflda) return false;
            if (c == Code.Ldsfld && !IsStringEmpty(x)) return false;
            if (x.Operand is MethodReference r) {
                var t = r.DeclaringType.FullName;
                if (c == Code.Newobj) {
                    if (t != "System.Text.StringBuilder") return false;
                } else if (!(r is MethodDefinition d && d == dec) && t != "System.String" && t != "System.Text.StringBuilder")
                    return false;
            }
        }
        return true;
    }

    static string Esc(string s) {
        return s.Replace("\\", "\\\\").Replace("\n", "\\n").Replace("\r", "\\r").Replace("\t", "\\t");
    }

    // Value pushed by the instructions ending at index i: "#id" (decryptor call), "=literal" or null.
    static string Arg(IList<Instruction> ins, int i, MethodDefinition dec, ModuleDefinition mod, out int start) {
        start = i;
        var x = ins[i];
        if (IsStringEmpty(x)) return "=";
        if (x.OpCode == OpCodes.Ldstr) return "=" + (string)x.Operand;
        if (Local(x, mod) == dec && i > 0 && LdcI4(ins[i - 1], out var id)) { start = i - 1; return "#" + id; }
        return null;
    }

    static object[] DefaultArgs(MethodInfo m) {
        return m.GetParameters().Select(p => p.ParameterType.IsValueType ? Activator.CreateInstance(p.ParameterType) : null).ToArray();
    }

    // A decrypted string looks real if ≥ 95 % of its characters are printable (or ordinary
    // whitespace). Wrong keys produce either one constant value or binary-looking garbage.
    static bool Printable(string s) {
        if (s.Length == 0) return true;
        int ok = s.Count(ch => (!char.IsControl(ch) || ch == '\n' || ch == '\r' || ch == '\t')
            && ch != '\uFFFD' && !char.IsSurrogate(ch) && !(ch >= '\uE000' && ch <= '\uF8FF'));
        return ok >= 0.95 * s.Length;
    }

    static bool Sane(ICollection<string> values, out string why) {
        why = null;
        if (values.Count <= 10) return true;
        if (values.Distinct().Count() < 3) { why = "the same value for everything"; return false; }
        double good = values.Count(Printable) / (double)values.Count;
        if (good < 0.9) { why = $"garbage ({good:P0} of strings printable)"; return false; }
        return true;
    }

    static int Fail(string msg, int code) {
        Console.Error.WriteLine("ERROR: " + msg);
        return code;
    }

    static int Main(string[] args) {
        bool verify = args.Length > 0 && args[0] == "verify";
        if (verify ? args.Length < 5 : args.Length < 2) {
            Console.Error.WriteLine("usage: Extract.exe <EXAPUNKS.exe> <out.tsv>\n"
                + "       Extract.exe verify <patched EXAPUNKS.exe> <Language> <keys.tsv> <out.txt>");
            return 1;
        }
        var asmPath = verify ? args[1] : args[0];
        var asmDef = AssemblyDefinition.ReadAssembly(asmPath);
        var mod = asmDef.MainModule;

        var calls = new Dictionary<MethodDefinition, int>();
        foreach (var m in AllMethods(mod))
            foreach (var x in m.Body.Instructions) {
                var d = Local(x, mod);
                if (d != null) calls[d] = (calls.TryGetValue(d, out var c) ? c : 0) + 1;
            }

        var dec = calls.Keys.Where(m => m.IsStatic && m.ReturnType.FullName == "System.String"
                && m.Parameters.Count == 1 && m.Parameters[0].ParameterType.FullName == "System.Int32")
            .OrderByDescending(m => calls[m]).FirstOrDefault();
        if (dec == null) return Fail("no string decryptor (static string f(int)) found: unknown build", 3);
        var loc = calls.Keys.Where(m => m.IsStatic && m.ReturnType.Name == "LocString" && m.Parameters.Count == 2
                && m.Parameters.All(p => p.ParameterType.FullName == "System.String"))
            .OrderByDescending(m => calls[m]).FirstOrDefault();
        if (loc == null) return Fail("no localization lookup (static LocString f(string, string)) found: unknown build", 3);
        // The decryptor's key is derived once, on its first call, so the first call must come from
        // game code. Any game method that calls it before doing anything else will do; even if
        // the rest of that method throws, the key is already set up.
        var trigger = AllMethods(mod).Where(m => m.IsStatic && !m.HasGenericParameters
                && m.Parameters.All(p => p.ParameterType.FullName == "System.String" || p.ParameterType.IsPrimitive)
                && !m.DeclaringType.HasGenericParameters && !m.IsConstructor && m.Body.Instructions.Count >= 2
                && LdcI4(m.Body.Instructions[0], out _) && Local(m.Body.Instructions[1], mod) == dec
                && IsPure(m, dec))
            .OrderBy(m => m.Body.Instructions.Count).FirstOrDefault();
        if (trigger == null) return Fail("no side-effect-free trigger method found", 3);
        Console.Error.WriteLine($"decryptor {dec.DeclaringType.Name}::{dec.Name} ({calls[dec]} calls)");
        Console.Error.WriteLine($"L()       {loc.DeclaringType.Name}::{loc.Name} ({calls[loc]} calls)");
        Console.Error.WriteLine($"trigger   {trigger.DeclaringType.Name}::{trigger.Name}");

        // Collect (text, context, hint) at every L() call site, in program order.
        var sites = new List<string[]>();
        int dynamic = 0;
        foreach (var m in AllMethods(mod)) {
            var ins = m.Body.Instructions;
            for (int i = 2; i < ins.Count; i++) {
                if (Local(ins[i], mod) != loc) continue;
                var ctx = Arg(ins, i - 1, dec, mod, out int s2);
                var txt = ctx == null || s2 < 1 ? null : Arg(ins, s2 - 1, dec, mod, out _);
                if (txt == null) { dynamic++; continue; }
                var t = m.DeclaringType;
                while (t.DeclaringType != null && t.Name.StartsWith("<")) t = t.DeclaringType;
                var hint = t.Name.StartsWith("#=") ? "" : t.Name;
                sites.Add(new[] { txt, ctx, hint });
            }
        }
        Console.Error.WriteLine($"{sites.Count} literal call sites, {dynamic} with computed text (skipped)");
        if (dynamic > 0)
            Console.Error.WriteLine($"WARNING: {dynamic} call sites pass computed text; those strings are not listed "
                + "and will stay English unless found another way");

        // Decrypt via reflection, after letting the trigger initialize the decryptor.
        var asm = Assembly.LoadFrom(asmPath);
        var rmod = asm.ManifestModule;
        var rtrig = (MethodInfo)rmod.ResolveMethod(trigger.MetadataToken.ToInt32());
        try { rtrig.Invoke(null, DefaultArgs(rtrig)); }
        catch (Exception e) { Console.Error.WriteLine("trigger threw (harmless): " + (e.InnerException ?? e).GetType().Name); }
        var rdec = (MethodInfo)rmod.ResolveMethod(dec.MetadataToken.ToInt32());
        var cache = new Dictionary<string, string>();
        foreach (var a in sites.SelectMany(s => s.Take(2)).Where(a => a.StartsWith("#")).Distinct())
            cache[a] = (string)rdec.Invoke(null, new object[] { int.Parse(a.Substring(1)) });
        if (!Sane(cache.Values, out var why))
            return Fail($"decryption returned {why}: key derivation failed, nothing written", 2);
        Func<string, string> val = a => a.StartsWith("=") ? a.Substring(1) : cache[a];

        if (verify) return Verify(asm, rmod, loc, args);

        var seen = new HashSet<string>();
        int n = 0;
        using (var w = new StreamWriter(args[1], false, new UTF8Encoding(false))) {
            w.WriteLine("english\tcontext\thint");
            foreach (var s in sites) {
                var text = val(s[0]); var ctx = val(s[1]);
                if (text.Length == 0 || !seen.Add(text + "\u0001" + ctx)) continue;
                w.WriteLine(Esc(text) + "\t" + Esc(ctx) + "\t" + s[2]);
                n++;
            }
        }
        Console.Error.WriteLine($"{n} distinct strings written to {args[1]}");
        return 0;
    }

    static int Verify(Assembly asm, Module rmod, MethodDefinition loc, string[] args) {
        // loader: the static void () next to L() that reads the file (File.ReadAllText)
        var loaders = loc.DeclaringType.Methods.Where(m => m.IsStatic && !m.HasParameters && m.HasBody
            && m.ReturnType.FullName == "System.Void"
            && m.Body.Instructions.Any(x => x.Operand is MethodReference r && r.Name == "ReadAllText")).ToList();
        if (loaders.Count != 1) return Fail($"expected one strings.csv loader next to L(), found {loaders.Count}", 3);
        var loader = loaders[0];
        Console.Error.WriteLine($"loader    {loader.DeclaringType.Name}::{loader.Name}");

        // The current-language setting: static Language fields of the localization class, plus any
        // static Language field the LocString getters read. Only those are set.
        var fields = new HashSet<FieldDefinition>(loc.DeclaringType.Fields.Where(f => f.IsStatic && !f.IsLiteral
            && !f.IsInitOnly && f.FieldType.Name == "Language"));
        var locString = loc.ReturnType.Resolve();
        if (locString != null)
            foreach (var m in locString.Methods.Where(m => m.HasBody))
                foreach (var x in m.Body.Instructions)
                    if (x.OpCode == OpCodes.Ldsfld && x.Operand is FieldDefinition f && f.FieldType.Name == "Language"
                        && f.IsStatic && !f.IsLiteral && !f.IsInitOnly)
                        fields.Add(f);
        if (fields.Count == 0) return Fail("no current-language field found", 3);
        var langT = asm.GetType("Language");
        if (langT == null) return Fail("enum Language not found", 3);
        object lang;
        try { lang = Enum.Parse(langT, args[2]); }
        catch (ArgumentException) { return Fail($"'{args[2]}' is not a value of enum Language", 1); }
        foreach (var f in fields) {
            rmod.ResolveField(f.MetadataToken.ToInt32()).SetValue(null, lang);
            Console.Error.WriteLine($"language  {f.DeclaringType.Name}::{f.Name} = {args[2]}");
        }

        rmod.ResolveMethod(loader.MetadataToken.ToInt32()).Invoke(null, null);
        var L = rmod.ResolveMethod(loc.MetadataToken.ToInt32());
        int n = 0;
        Func<string, string> un = s => s.Replace("\\\\", "\u0001").Replace("\\n", "\n").Replace("\\t", "\t")
            .Replace("\\r", "\r").Replace("\u0001", "\\");
        using (var w = new StreamWriter(args[4], false, new UTF8Encoding(false)))
            foreach (var line in File.ReadAllLines(args[3], Encoding.UTF8)) {
                var kc = line.Split('\t');
                var r = L.Invoke(null, new object[] { un(kc[0]), kc.Length > 1 ? un(kc[1]) : "" }).ToString();
                w.Write(Esc(r) + "\n");
                n++;
            }
        Console.Error.WriteLine($"looked up {n} keys");
        return 0;
    }
}
