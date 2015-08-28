##############################################################################
# Copyright (c) 2007,2015 Hajime Nakagami<nakagami@gmail.com>
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
import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows import Forms
from System.IO import FileMode, BinaryWriter, BinaryReader, IsolatedStorage
import marshal


def userpref_save(v, filename):
    stream = IsolatedStorage(filename, FileMode.Create)
    sw = BinaryWriter(stream)
    sw.Write(marshal.dumps(v))
    sw.Close()
    stream.Close()


def userpref_load(filename):
    stream = IsolatedStorage(filename, FileMode.Open)
    sr = BinaryReader(stream)
    v = marshal.loads(sr.ReadString())
    sr.Close()
    stream.Close()
    return v


def build_menu(menuStrip, menu_params):
    d = {}
    for menu in menu_params:
        m = Forms.ToolStripMenuItem()
        m.Text = menu[1]
        d[menu[0]] = m
        for item in menu[2]:
            if item[1] == '-':
                mi = Forms.ToolStripSeparator()
            else:
                mi = Forms.ToolStripMenuItem()
                mi.Tag = item[0]
                mi.Text = item[1]
                d[item[0]] = mi
            if item[2]:
                mi.Click += item[2]
            m.DropDownItems.Add(mi)
        menuStrip.Items.Add(m)
    return d


def build_context_menu(contextMenuStrip, menu_params):
    d = {}
    for item in menu_params:
        if item[1] == '-':
            mi = Forms.ToolStripSeparator()
        else:
            mi = Forms.ToolStripMenuItem()
            mi.Tag = item[0]
            mi.Text = item[1]
            d[item[0]] = mi
        if item[2]:
            mi.Click += item[2]
        contextMenuStrip.Items.Add(mi)
    return d


def build_tool_strip(toolStrip, menu_params):
    return build_context_menu(toolStrip, menu_params)


def ClearGrid(grid, caps=[]):
    grid.DataSource = None
    grid.Rows.Clear()
    grid.Columns.Clear()
    grid.AllowUserToAddRows = False
    grid.EditMode = Forms.DataGridViewEditMode.EditProgrammatically
    grid.ColumnCount = len(caps)
    for i in range(grid.ColumnCount):
        grid.Columns[i].Name = caps[i]


def ReaderToGrid(grid, reader):
    ClearGrid(grid)
    cname = [row['ColumnName'] for row in reader.GetSchemaTable().Rows]
    grid.ColumnCount = len(cname)
    for i in range(len(cname)):
        grid.Columns[i].Name = cname[i]
    for c in reader:
        row = [c[i] for i in range(len(cname))]
        if len(row) == 1 and type(row[0]) == int:
            row[0] = str(row[0])
        grid.Rows.Add(*row)


def DictToGrid(grid, d, key_name='Name', value_name='Value'):
    ClearGrid(grid, caps=[key_name, value_name])
    for k in d:
        grid.Rows.Add(*[k, d[k]])


def DictListToGrid(grid, dlist):
    if len(dlist) == 0:
        ClearGrid(grid)
        return
    cname = dlist[0].keys()
    ClearGrid(grid, caps=cname)
    for c in dlist:
        row = [str(c[k]).strip() for k in cname]
        if len(row) == 1 and type(row[0]) == int:
            row[0] = str(row[0])
        grid.Rows.Add(*row)


def DataTableToGrid(grid, datatable, tabname, columns):
    ClearGrid(grid)
    bs = Forms.BindingSource()
    bs.DataSource = datatable
    grid.DataSource = bs
    for c in columns:
        cname = c['NAME'].strip()
        tname = c['TYPE_NAME'].strip()
        if tname == 'DATE':
            grid.Columns[cname].DefaultCellStyle.Format = "d"
        if tname == 'TIME':
            grid.Columns[cname].DefaultCellStyle.Format = "T"
