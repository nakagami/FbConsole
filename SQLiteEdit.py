##############################################################################
# Copyright (c) 2007, Hajime Nakagami<nakagami@da2.so-net.ne.jp>
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
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
clr.AddReference("System.Data")
from System.Windows import Forms
from System.Drawing import Size, Color
from System.Data import *
from System.IO import Path
from System.Text.RegularExpressions import Regex, RegexOptions
from System.Convert import IsDBNull
import sqliteutil

PK_COLOR = Color.Yellow
FK_COLOR = Color.Green
PK_FK_COLOR = Color.YellowGreen
UK_COLOR = Color.LightGray

INPUT_COLOR = Color.LightYellow
NEW_DATA_COLOR = Color.LightBlue

class SQLiteEditForm(Forms.Form):
    def __init__(self, filename):
        self.filename = filename

        self.SuspendLayout()
        self._list = Forms.ListBox()
        self._list.Dock = Forms.DockStyle.Fill
        self._list.TabIndex = 1
        self._list.DoubleClick += self.OnTableSelect
        self._dg = Forms.DataGridView()
        self._dg.DefaultCellStyle.NullValue = '<Null>'
        self._dg.ColumnHeadersHeightSizeMode = \
                    Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
        self._dg.AutoSizeColumnsMode = \
                    Forms.DataGridViewAutoSizeColumnsMode.AllCells
        self._dg.ColumnHeadersHeightSizeMode = \
                    Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
        self._dg.AutoSizeColumnsMode = \
                    Forms.DataGridViewAutoSizeColumnsMode.AllCells
        self._dg.AllowUserToAddRows = False
        self._dg.AllowUserToDeleteRows = False
        self._dg.EditMode = Forms.DataGridViewEditMode.EditProgrammatically
        self._dg.Dock = Forms.DockStyle.Fill
        self._dg.TabIndex = 2
        self._dg.RowValidated += self.OnRowValidated
        self._dg.RowsAdded += self.OnRowsAdded
        self._dg.UserDeletingRow += self.OnUserDeletingRow
        self._dg.DataError += self.OnDataGridViewDataError

        # SplitContainer
        self._split = Forms.SplitContainer()
        self._split.Dock = Forms.DockStyle.Fill
        self._split.Orientation = Forms.Orientation.Vertical
        self._split.Panel1.Controls.Add(self._list)
        self._split.Panel2.Controls.Add(self._dg)

        # Form
        self.Text = self.filename
        self.AutoScaleMode = Forms.AutoScaleMode.Font
        self.Controls.Add(self._split)
        self.ResumeLayout(False)
        self.PerformLayout()
        self.Closed += self.OnClose
        try:
            self.db_conn = sqliteutil.SQLiteDatabase(filename)
            self.db_conn.open()
            for s in self.db_conn.tables():
               self._list.Items.Add(s)
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Can't open database")
            self.db_conn = None

    def OnTableSelect(self, sender, args):
        self.tab_name = self._list.SelectedItem
        self.Text = ''.join([self.filename, '[', self.tab_name, ']'])
        self._dg.RowsAdded -= self.OnRowsAdded
        data_adapter = self.db_conn.table_adapter(self.tab_name)
        data_table = DataTable()
        data_table.ColumnChanging += self.OnColumnChanging
        data_table.Clear()
        data_adapter.Fill(data_table)
        bs = Forms.BindingSource()
        bs.DataSource = data_table
        self._dg.DataSource = bs
        data_adapter.Dispose()
        self.table_pks = self.db_conn.primary_keys(self.tab_name)
        table_fks = []
        fks = self.db_conn.foreign_keys(self.tab_name, False)
        for fk in fks:
            table_fks.extend(fks[fk]['COLUMN_NAME'])
        table_uks = self.db_conn.unique_keys(self.tab_name)
        if len(self.table_pks):
            self._dg.EditMode = Forms.DataGridViewEditMode.EditOnKeystrokeOrF2
            self._dg.AllowUserToDeleteRows = True
            self._dg.AllowUserToAddRows = True
        self._dg.RowsAdded += self.OnRowsAdded
        for c in self._dg.Columns:
            c.SortMode = Forms.DataGridViewColumnSortMode.NotSortable
            if c.Name in self.table_pks and c.Name in table_fks:
                c.DefaultCellStyle.BackColor = PK_FK_COLOR
            elif c.Name in self.table_pks:
                c.DefaultCellStyle.BackColor = PK_COLOR
            elif c.Name in table_fks:
                c.DefaultCellStyle.BackColor = FK_COLOR
            elif c.Name in table_uks:
                c.DefaultCellStyle.BackColor = UK_COLOR

    def OnDataGridViewDataError(self, sender, args):
        if args.Exception and args.Exception.Message != 'UserWarning':
            Forms.MessageBox.Show(args.Exception.Message, 'Error')

    def OnColumnChanging(self, sender, args):
        if self._dg.CurrentRow.Cells[0].Style.BackColor == INPUT_COLOR:
            return
        cond = ''
        params = {'@0':args.ProposedValue}
        for i in range(len(self._dg.DataSource.DataSource.Columns)):
            cname = self._dg.DataSource.DataSource.Columns[i].ColumnName
            if cname in self.table_pks:
                if len(cond):
                    cond += ' and '
                params['@' + cname] = args.Row[i]
                cond += cname + "=@" + cname
        sql = 'update %s set %s=@0'  % (self.tab_name, args.Column.ColumnName)
        sql += ' where ' + cond
        self.db_conn.execute_noq(sql, params)

    def OnRowValidated(self, sender, args):
        ri = args.RowIndex
        if self._dg.Rows[ri].Cells[0].Style.BackColor == INPUT_COLOR:
            cnames = []
            values = {}
            for ci in range(self._dg.ColumnCount):
                if not IsDBNull(self._dg.Rows[ri].Cells[ci].Value):
                    cname = self._dg.Columns[ci].Name
                    cnames.append(cname)
                    values['@'+cname] = self._dg.Rows[ri].Cells[ci].Value
            sql = 'insert into "' + self.tab_name + '" ("' 
            sql += '","'.join(cnames)
            sql += '") values (@' + ',@'.join(cnames) + ')'
            
            try:
                self.db_conn.execute_noq(sql, values)
                if set(self.table_pks) - set(cnames) != set([]):
                    read_only = True
                else:
                    read_only = False
                for ci in range(self._dg.ColumnCount):
                    cell = self._dg.Rows[ri].Cells[ci]
                    cell.Style.BackColor = NEW_DATA_COLOR
                    if read_only:
                        cell.ReadOnly = True
            except Exception, e:
                Forms.MessageBox.Show(str(e), "Error")

    def OnRowsAdded(self, sender, args):
        ri = args.RowIndex -1
        for ci in range(self._dg.ColumnCount):
            self._dg.Rows[ri].Cells[ci].Style.BackColor = INPUT_COLOR

    def OnUserDeletingRow(self, sender, args):
        if args.Row.Cells[0].Style.BackColor == INPUT_COLOR:
            return
        if len(self.table_pks):
            cond = ''
            params = {}
            for i in range(len(self._dg.DataSource.DataSource.Columns)):
                cname = self._dg.DataSource.DataSource.Columns[i].ColumnName
                if cname in self.table_pks:
                    if IsDBNull(args.Row.Cells[i].Value):
                        raise UserWarning, "Can't delete."
                    if len(cond):
                        cond += ' and '
                    params['@' + cname] = args.Row.Cells[i].Value
                    cond += cname + "=@" + cname
            sql = 'delete from ' + self.tab_name + ' where ' + cond
            self.db_conn.execute_noq(sql, params)
            return
        args.Cancel = True

    def OnClose(self, sender, args):
        pass
    
if __name__ == '__main__':
    ofd = Forms.OpenFileDialog()
    ofd.AddExtension = True
    r = ofd.ShowDialog()
    if r == Forms.DialogResult.OK:
        app = SQLiteEditForm(ofd.FileName)
        Forms.Application.Run(app)

