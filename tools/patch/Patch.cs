// Patch EXAPUNKS.exe so its LocString display getter falls back to English when the selected
// language has no entry, an empty entry, or only the "[!!! MISSING !!!]" placeholder. Without this, setting the
// game language to anything but English breaks puzzle briefings (they are only loaded for English)
// and dialogue (the vignette parser never fills German/Russian, and the French/Chinese/Japanese
// columns of the shipped dialogue files are empty). Located by structure, not tokens.
//   mono Patch.exe <original EXAPUNKS.exe> <output exe>
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class Patch {
    static int Main(string[] args) {
        var asm = AssemblyDefinition.ReadAssembly(args[0]);
        var mod = asm.MainModule;
        var loc = mod.Types.FirstOrDefault(t => t.Name == "LocString");
        // The display getter: instance string (), body = ldarg0; ldfld dict; ldsfld Language; callvirt get_Item; ret
        var matches = loc == null ? new MethodDefinition[0] : loc.Methods.Where(m => !m.IsStatic && m.HasBody
            && m.ReturnType.FullName == "System.String" && m.Parameters.Count == 0
            && m.Body.Instructions.Count == 5 && m.Body.Instructions[2].OpCode == OpCodes.Ldsfld
            && ((FieldReference)m.Body.Instructions[2].Operand).FieldType.Name == "Language").ToArray();
        if (matches.Length != 1) {
            Console.Error.WriteLine("getter not found (" + matches.Length + " candidates): exe already patched or unknown build");
            return 2;
        }
        var getter = matches[0];
        var dictField = (FieldReference)getter.Body.Instructions[1].Operand;
        var langField = (FieldReference)getter.Body.Instructions[2].Operand;
        var getItem = (MethodReference)getter.Body.Instructions[3].Operand;
        // TryGetValue on the same Dictionary<Language,string>
        var dictType = (GenericInstanceType)dictField.FieldType;
        var tryGet = new MethodReference("TryGetValue", mod.TypeSystem.Boolean, dictType) { HasThis = true };
        tryGet.Parameters.Add(new ParameterDefinition(((GenericInstanceType)dictType).ElementType.GenericParameters[0]));
        tryGet.Parameters.Add(new ParameterDefinition(new ByReferenceType(((GenericInstanceType)dictType).ElementType.GenericParameters[1])) { IsOut = true });
        var isNullOrEmpty = mod.ImportReference(typeof(string).GetMethod("IsNullOrEmpty", new[] { typeof(string) }));
        var startsWith = mod.ImportReference(typeof(string).GetMethod("StartsWith", new[] { typeof(string), typeof(StringComparison) }));
        Console.WriteLine("patching " + loc.FullName + "::" + getter.Name);

        var body = getter.Body;
        body.Instructions.Clear();
        body.Variables.Clear();
        var s = new VariableDefinition(mod.TypeSystem.String);
        body.Variables.Add(s);
        body.InitLocals = true;
        var il = body.GetILProcessor();
        var fallback = il.Create(OpCodes.Ldarg_0);
        // if (dict.TryGetValue(lang, out s) && !string.IsNullOrEmpty(s)
        //     && !s.StartsWith("[!!! MISSING", StringComparison.Ordinal)) return s;
        il.Append(il.Create(OpCodes.Ldarg_0));
        il.Append(il.Create(OpCodes.Ldfld, dictField));
        il.Append(il.Create(OpCodes.Ldsfld, langField));
        il.Append(il.Create(OpCodes.Ldloca_S, s));
        il.Append(il.Create(OpCodes.Callvirt, tryGet));
        il.Append(il.Create(OpCodes.Brfalse_S, fallback));
        il.Append(il.Create(OpCodes.Ldloc, s));
        il.Append(il.Create(OpCodes.Call, isNullOrEmpty));
        il.Append(il.Create(OpCodes.Brtrue_S, fallback));
        il.Append(il.Create(OpCodes.Ldloc, s));
        il.Append(il.Create(OpCodes.Ldstr, "[!!! MISSING"));
        il.Append(il.Create(OpCodes.Ldc_I4_4));   // StringComparison.Ordinal
        il.Append(il.Create(OpCodes.Callvirt, startsWith));
        il.Append(il.Create(OpCodes.Brtrue_S, fallback));
        il.Append(il.Create(OpCodes.Ldloc, s));
        il.Append(il.Create(OpCodes.Ret));
        // return dict[English];
        il.Append(fallback);
        il.Append(il.Create(OpCodes.Ldfld, dictField));
        il.Append(il.Create(OpCodes.Ldc_I4_1));
        il.Append(il.Create(OpCodes.Callvirt, getItem));
        il.Append(il.Create(OpCodes.Ret));
        asm.Write(args[1]);
        Console.WriteLine("written " + args[1]);
        return 0;
    }
}
