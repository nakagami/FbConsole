##############################################################################
# Copyright (c) 2007-2009, Hajime Nakagami<nakagami@da2.so-net.ne.jp>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
##############################################################################
import clr, sys
clr.AddReferenceByPartialName("IronPython")
import IronPython.Hosting as Hosting
import System
import System.IO
import System.Environment
from FbConsole import APP_NAME, __version__, img_files

src = ['FbConsole.py', 'FbSqlForm.py', 'dialogform.py', 
    'fbutil.py', 'fbddl.py', 'formutil.py']
dll_libs = ['FirebirdSql.Data.FirebirdClient.dll']
dir_name = ''.join([APP_NAME, '_', __version__.replace('.','_')])
out_name = '/'.join([dir_name, APP_NAME])
out_file = out_name + '.exe'
pdb_file = '/'.join([dir_name, APP_NAME + '.pdb'])
main_module = 'FbConsole.py'

print "Target directory is '%s'..." % (dir_name, )
System.IO.Directory.CreateDirectory(dir_name)

print "Compile '%s'." % (out_file, )
from System.Collections.Generic import List
from IronPython.Runtime.Operations import PythonOps
from System.Reflection import Emit
from System.Reflection.Emit import OpCodes, AssemblyBuilderAccess
from System.Reflection import AssemblyName, TypeAttributes, MethodAttributes

clr.CompileModules(out_name + '.dll', mainModule = main_module, *src)
aName = AssemblyName(System.IO.FileInfo(out_name).Name)
ab = PythonOps.DefineDynamicAssembly(aName, AssemblyBuilderAccess.RunAndSave)
mb = ab.DefineDynamicModule(out_name,  aName.Name + '.exe')
tb = mb.DefineType('PythonMain', TypeAttributes.Public)
mainMethod = tb.DefineMethod('Main', MethodAttributes.Public | MethodAttributes.Static, int, ())
gen = mainMethod.GetILGenerator()

# get the ScriptCode assembly...    
gen.Emit(OpCodes.Ldstr, aName.Name + ".dll")
gen.EmitCall(OpCodes.Call, clr.GetClrType(System.IO.Path).GetMethod("GetFullPath", (clr.GetClrType(str), )), ())
gen.EmitCall(OpCodes.Call, clr.GetClrType(System.Reflection.Assembly).GetMethod("LoadFile", (clr.GetClrType(str), )), ())

# emit module name
gen.Emit(OpCodes.Ldstr, System.IO.Path.GetFileNameWithoutExtension(main_module))

gen.Emit(OpCodes.Ldnull)

# call InitializeModule
gen.EmitCall(OpCodes.Call, clr.GetClrType(PythonOps).GetMethod("InitializeModule"), ())    
gen.Emit(OpCodes.Ret)

tb.CreateType()
ab.SetEntryPoint(mainMethod, 
        System.Reflection.Emit.PEFileKinds.WindowApplication)
ab.Save(aName.Name + '.exe', 
        System.Reflection.PortableExecutableKinds.ILOnly,
        System.Reflection.ImageFileMachine.I386)
System.IO.File.Delete(out_file)
System.IO.File.Move(aName.Name + '.exe', out_file)

print "Copy images to '%s/res'." % (dir_name)
System.IO.Directory.CreateDirectory(dir_name + '/' +'res')
for f in img_files:
    fname = f + '.png'
    System.IO.File.Copy(
        'res/' + fname, '/'.join([dir_name, 'res', fname]), True)

search_path = ['.']
for dir in System.Environment.GetEnvironmentVariable('PATH').split(';'):
    if dir[-1] == '/':
        dir = dir[:-1]
    search_path.append(dir)

for f in dll_libs:
    for dir in sys.path:
        src = dir + '/' + f
        if System.IO.File.Exists(src):
            dest = '/'.join([dir_name, f])
            System.IO.File.Copy(src, dest, True)
            print "Copy '%s' from '%s' to '%s'." % (f, dir, dir_name)
            break
