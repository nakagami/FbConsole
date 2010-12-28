##############################################################################
# Copyright (c) 2007-2008, Hajime Nakagami<nakagami@da2.so-net.ne.jp>
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
from System.Windows import Forms
from System.Drawing import Size

def charset_list():
    return [
        "NONE", "ASCII", "UNICODE_FSS", "UTF8", "OCTETS", 
        #from fbintl.conf <charset ????>
        "SJIS_0208", "EUCJ_0208", "DOS437", "DOS850", "DOS865",
        "ISO8859_1", "ISO8859_2", "ISO8859_3", "ISO8859_4", "ISO8859_5",
        "ISO8859_6", "ISO8859_7", "ISO8859_8", "ISO8859_9", "ISO8859_13",
        "DOS852", "DOS857", "DOS860", "DOS861", "DOS863", "CYRL", "DOS737", 
        "DOS775", "DOS858", "DOS862", "DOS864", "DOS866", "DOS869",
        "WIN1250", "WIN1251", "WIN1252", "WIN1253", "WIN1254", "NEXT",
        "WIN1255", "WIN1256", "WIN1257", "KSC_5601", "BIG_5", "GB_2312",
        "KOI8R", "KOI8U", "WIN1258", "TIS620", "GBK", "CP943C",
    ]


class SimpleTextForm(Forms.Form):
    def __init__(self, title, s):
        self.Width = 470
        self.Height = 240
        self.Text = title

        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self._tx = Forms.TextBox(Left=5, Top=5, Width=450, Height=200)
        self._tx.Multiline = True
        self._tx.ReadOnly = True
        self._tx.ScrollBars = Forms.ScrollBars.Vertical
        self._tx.Text = '\r\n'.join(s.strip().split('\n'))
        self.Controls.Add(self._tx)
        

class SimpleInputForm(Forms.Form):
    def __init__(self, title, text):
        self.Width = 600
        self.Height = 100
        self.Text = title

        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self._tx = Forms.TextBox(Left=20, Top=9, Width=560)
        self._tx.Text = text
        self._tx.TabIndex = 1
        self.Controls.Add(self._tx)

        self.AcceptButton = Forms.Button(Text="&OK", Left=420, Top=40)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 2
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=500, Top=40)
        self.CancelButton.TabIndex = 3
        self.Controls.Add(self.CancelButton)

    def OnOk(self, sender, args):
        self.DialogResult = Forms.DialogResult.OK
        self.text = self._tx.Text
        self.Close()


class SimpleSqlForm(Forms.Form):
    def __init__(self, conn, sql, read_only = False):
        self.conn = conn
        self.Width = 600
        self.Height = 100
        self.Text = 'SQL'

        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self._tx = Forms.TextBox(Left=20, Top=9, Width=560)
        self._tx.Text = sql
        self._tx.ReadOnly = read_only
        self._tx.TabIndex = 1
        self.Controls.Add(self._tx)

        self.AcceptButton = Forms.Button(Text="&OK", Left=420, Top=40)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 2
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=500, Top=40)
        self.CancelButton.TabIndex = 3
        self.Controls.Add(self.CancelButton)

    def OnOk(self, sender, args):
        try:
            self.conn.execute_noq(self._tx.Text)
            self.DialogResult = Forms.DialogResult.OK
            self.Close()
        except Exception, e:
            Forms.MessageBox.Show(str(e), "Error")


class UserPasswordForm(Forms.Form):
    def __init__(self, conn_dict):
        self.conn_dict = conn_dict
        self.Width = 360
        self.Height = 145
        self.Text = 'User & Password'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=12, Text="User", AutoSize=True))
        self._user = Forms.TextBox(Left=80, Top=9, Width=250)
        self._user.TabIndex = 1
        self.Controls.Add(self._user)
        self.Controls.Add(
            Forms.Label(Left=12, Top=43, Text="Password", AutoSize=True))
        self._password = Forms.TextBox(Left=80, Top=38, Width=250)
        self._password.PasswordChar = '*'
        self._password.TabIndex = 2
        self.Controls.Add(self._password)

        self._savePassword = Forms.CheckBox(
            Left=30, Top=64, Text="Save Password", AutoSize=True)
        if int(self.conn_dict.get('SAVE_PASS_FLAG', '0')):
            self._savePassword.Checked = True
        self._savePassword.TabIndex = 3
        self.Controls.Add(self._savePassword)
        
        self.AcceptButton = Forms.Button(Text="&OK", Left=60, Top=90)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 4
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=220, Top=90)
        self.CancelButton.TabIndex = 5
        self.Controls.Add(self.CancelButton)

        self._user.Text = self.conn_dict['User']
        self._password.Text = self.conn_dict.get('Password')

    def OnOk(self, sender, args):
        self.conn_dict['PrevUser'] = self.conn_dict['User']
        self.conn_dict['PrevPassword'] = self.conn_dict['Password']
        self.conn_dict['User'] = self._user.Text
        self.conn_dict['Password'] = self._password.Text
        if self._savePassword.Checked:
            self.conn_dict['SAVE_PASS_FLAG'] = '1'
        else:
            self.conn_dict['SAVE_PASS_FLAG'] = '0'
        self.DialogResult = Forms.DialogResult.OK


class CopyTableForm(Forms.Form):
    def __init__(self, text):
        self.Width = 600
        self.Height = 100
        self.Text = 'Copy Table'

        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self._tx = Forms.TextBox(Left=20, Top=9, Width=560)
        self._tx.Text = text
        self._tx.TabIndex = 1
        self.Controls.Add(self._tx)

        self._schemaOnly = Forms.CheckBox(
            Left=30, Top=30, Text="Schema Only", AutoSize=True)
        self._schemaOnly.Checked = True
        self._schemaOnly.TabIndex = 2
        self.Controls.Add(self._schemaOnly)

        self.AcceptButton = Forms.Button(Text="&OK", Left=420, Top=40)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 3
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=500, Top=40)
        self.CancelButton.TabIndex = 4
        self.Controls.Add(self.CancelButton)

    def OnOk(self, sender, args):
        self.DialogResult = Forms.DialogResult.OK
        self.text = self._tx.Text
        self.schema_only = self._schemaOnly.Checked
        self.Close()


class UserAddForm(Forms.Form):
    def __init__(self):
        self.Width = 360
        self.Height = 260
        self.Text = 'User Add'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=12, Text="User", AutoSize=True))
        self._user = Forms.TextBox(Left=100, Top=9, Width=230)
        self._user.CharacterCasing = Forms.CharacterCasing.Upper
        self._user.TabIndex = 1
        self.Controls.Add(self._user)

        self.Controls.Add(
            Forms.Label(Left=12, Top=42, Text="Pass", AutoSize=True))
        self._password = Forms.TextBox(Left=100, Top=39, Width=230)
        self._password.PasswordChar = '*'
        self._password.TabIndex = 2
        self.Controls.Add(self._password)

        self.Controls.Add(
            Forms.Label(Left=12, Top=72, Text="Pass(confirm)", 
            AutoSize=True))
        self._password2 = Forms.TextBox(Left=100, Top=69, Width=230)
        self._password2.PasswordChar = '*'
        self._password2.TabIndex = 3
        self.Controls.Add(self._password2)

        self.Controls.Add(
            Forms.Label(Left=12, Top=122, Text="First Name", AutoSize=True))
        self._first = Forms.TextBox(Left=100, Top=119, Width=230)
        self._first.TabIndex = 4
        self.Controls.Add(self._first)

        self.Controls.Add(
            Forms.Label(Left=12, Top=152, Text="Middle Name", AutoSize=True))
        self._middle = Forms.TextBox(Left=100, Top=149, Width=230)
        self._middle.TabIndex = 5
        self.Controls.Add(self._middle)

        self.Controls.Add(
            Forms.Label(Left=12, Top=182, Text="Last Name", AutoSize=True))
        self._last = Forms.TextBox(Left=100, Top=179, Width=230)
        self._last.TabIndex = 6
        self.Controls.Add(self._last)

        self.AcceptButton = Forms.Button(Text="&OK", Left=60, Top=210)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 7
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=220, Top=210)
        self.CancelButton.TabIndex = 8
        self.Controls.Add(self.CancelButton)

    def OnOk(self, sender, args):
        if not self._user.Text:
            Forms.MessageBox.Show('Enter User', 'Error')
            return
        if self._password.Text != self._password2.Text:
            Forms.MessageBox.Show('Pass does not match confirm', 'Error')
            return
        if not self._password.Text:
            Forms.MessageBox.Show('Require pass', 'Error')
            return
        self.DialogResult = Forms.DialogResult.OK


class UserModForm(Forms.Form):
    def __init__(self, user, first, middle, last):
        self.Width = 360
        self.Height = 260
        self.Text = 'User information modify'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=12, Text="User", AutoSize=True))
        self._user = Forms.TextBox(Left=100, Top=9, Width=230)
        self._user.CharacterCasing = Forms.CharacterCasing.Upper
        self._user.TabIndex = 1
        self._user.ReadOnly = True
        self._user.Text = user
        self.Controls.Add(self._user)

        self.Controls.Add(
            Forms.Label(Left=12, Top=42, Text="Pass", AutoSize=True))
        self._password = Forms.TextBox(Left=100, Top=39, Width=230)
        self._password.PasswordChar = '*'
        self._password.TabIndex = 2
        self.Controls.Add(self._password)

        self.Controls.Add(
            Forms.Label(Left=12, Top=72, Text="Pass(confirm)", 
            AutoSize=True))
        self._password2 = Forms.TextBox(Left=100, Top=69, Width=230)
        self._password2.PasswordChar = '*'
        self._password2.TabIndex = 3
        self.Controls.Add(self._password2)

        self.Controls.Add(
            Forms.Label(Left=12, Top=122, Text="First Name", AutoSize=True))
        self._first = Forms.TextBox(Left=100, Top=119, Width=230)
        self._first.TabIndex = 4
        self._first.Text = first
        self.Controls.Add(self._first)

        self.Controls.Add(
            Forms.Label(Left=12, Top=152, Text="Middle Name", AutoSize=True))
        self._middle = Forms.TextBox(Left=100, Top=149, Width=230)
        self._middle.TabIndex = 5
        self._middle.Text = middle
        self.Controls.Add(self._middle)

        self.Controls.Add(
            Forms.Label(Left=12, Top=182, Text="Last Name", AutoSize=True))
        self._last = Forms.TextBox(Left=100, Top=179, Width=230)
        self._last.TabIndex = 6
        self._last.Text = last
        self.Controls.Add(self._last)

        self.AcceptButton = Forms.Button(Text="&OK", Left=60, Top=210)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 7
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=220, Top=210)
        self.CancelButton.TabIndex = 8
        self.Controls.Add(self.CancelButton)

    def OnOk(self, sender, args):
        if not self._user.Text:
            Forms.MessageBox.Show('Enter User', 'Error')
            return
        if self._password.Text != self._password2.Text:
            Forms.MessageBox.Show('Pass does not match confirm', 'Error')
            return
        if not self._password.Text:
            Forms.MessageBox.Show('Require pass', 'Error')
            return
        self.DialogResult = Forms.DialogResult.OK


class ServerPropForm(Forms.Form):
    def __init__(self, alias_name=None, server_name=None):
        self.Width = 380
        self.Height = 150
        self.Text = 'Server property'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=22, Text="Server Alias", AutoSize=True))
        self._alias = Forms.TextBox(Left=92, Top=19, Width=250)
        self._alias.TabIndex = 1
        self.Controls.Add(self._alias)
        self.Controls.Add(
            Forms.Label(Left=12, Top=65, Text="Server Name", AutoSize=True))
        self._server = Forms.TextBox(Left=92, Top=58, Width=250)
        self._server.TabIndex = 2
        self.Controls.Add(self._server)
        
        self.AcceptButton = Forms.Button(Text="&Register", Left=70, Top=90)
        self.AcceptButton.Click += self.OnRegister
        self.AcceptButton.TabIndex = 3
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=220, Top=90)
        self.CancelButton.TabIndex = 4
        self.Controls.Add(self.CancelButton)

        if alias_name:
            self._alias.Text = alias_name
        if server_name:
            self._server.Text = server_name

    def OnRegister(self, sender, args):
        if not (self._server.Text or self._alias.Text):
            return
        if not self._alias.Text:
            self._alias.Text = self._server.Text
        self.DialogResult = Forms.DialogResult.OK
        self.Close()


class ConnPropForm(Forms.Form):
    def __init__(self, conn_d=None, require_server=False):
        self.Width = 450
        self.Height = 215
        self.Text = 'Connection Setting'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self.require_server = require_server

        if self.require_server:
            self.Controls.Add(Forms.Label(Left=3, Top=13, 
                            Text="Server name:", AutoSize=True))
            self._serverName = Forms.TextBox(Left=90, Top=10, Width=340)
            self._serverName.TabIndex = 1
            self.Controls.Add(self._serverName)
        else:
            self.Controls.Add(Forms.Label(Left=3, Top=13, 
                            Text="Display name:", AutoSize=True))
            self._displayName = Forms.TextBox(Left=90, Top=10, Width=340)
            self._displayName.TabIndex = 1
            self.Controls.Add(self._displayName)

        self.Controls.Add(
            Forms.Label(Left=3, Top=44, Text="Database path:", AutoSize=True))
        self._databasePath = Forms.TextBox(Left=90, Top=41, Width=310)
        self._databasePath.TabIndex = 2
        self.Controls.Add(self._databasePath)
        self._pathButton = Forms.Button(
                            Text="...", Left=406, Top=39, Size=Size(24,24))
        self._pathButton.Click += self.OnDbFileOpen
        self._pathButton.TabIndex = 3
        self.Controls.Add(self._pathButton)

        self.Controls.Add(
            Forms.Label(Left=3, Top=77, Text="Username:", AutoSize=True))
        self._userName = Forms.TextBox(Left=90, Top=74, Width=135)
        self._userName.TabIndex = 4
        self.Controls.Add(self._userName)

        self.Controls.Add(
            Forms.Label(Left=235, Top=77, Text="Password:", AutoSize=True))
        self._userPass = Forms.TextBox(Left=295, Top=74, Width=135)
        self._userPass.PasswordChar = '*'
        self._userPass.TabIndex = 5
        self.Controls.Add(self._userPass)

        self.Controls.Add(
            Forms.Label(Left=3, Top=102, Text="Role:", AutoSize=True))
        self._role = Forms.TextBox(Left=90, Top=97, Width=135)
        self._role.TabIndex = 6
        self.Controls.Add(self._role)

        self._savePassword = Forms.CheckBox(
            Left=300, Top=97, Text="Save Password", AutoSize=True)
        self._savePassword.TabIndex = 7
        self.Controls.Add(self._savePassword)

        self._charsetLabel = Forms.Label(
            Left=3, Top=130, Text="Charset:", AutoSize=True)
        self.Controls.Add(self._charsetLabel)
        self._charset = Forms.ComboBox(Left=90, Top=125, Width=106)
        for name in charset_list():
            self._charset.Items.Add(name)
        self._charset.Text = 'UNICODE_FSS'
        self._charset.TabIndex = 8
        self.Controls.Add(self._charset)

        self.Controls.Add(
            Forms.Label(Left=235, Top=130, Text="Port:", AutoSize=True))
        self._port = Forms.NumericUpDown(Left=295, Top=125, Width=135)
        self._port.Maximum = 65535
        self._port.Value = 3050
        self._port.TabIndex = 9
        self.Controls.Add(self._port)

        self.AcceptButton = Forms.Button(
                        Text="&OK", Left=267, Top=155, Size=Size(75,23))
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 10
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(
                        Text="&Cancel", Left=348, Top=155, Size=Size(75, 23))
        self.CancelButton.TabIndex = 11
        self.Controls.Add(self.CancelButton)

        if conn_d:
            if self.require_server:
                self._serverName.Text = conn_d.get('DataSource')
            else:
                self._displayName.Text = conn_d.get('DISPLAY_NAME')
            self._databasePath.Text = conn_d.get('Database')
            self._userName.Text = conn_d.get('User')
            self._userPass.Text = conn_d.get('Password')
            self._charset.Text = conn_d.get('Charset')
            self._role.Text = conn_d.get('Role')
            self._port.Value = int(conn_d.get('Port', 3050))
            if int(conn_d.get('SAVE_PASS_FLAG', '0')):
                self._savePassword.Checked = True
            else:
                self._savePassword.Checked = False

    def OnDbFileOpen(self, sender, args):
        ofd = Forms.OpenFileDialog()
        ofd.DefaultExt = '.fdb'
        ofd.AddExtension = True
        ofd.CheckFileExists = False
        ofd.Filter = 'Firebird databases (*.fdb)|*.fdb| All files (*.*)|*.*'
        r = ofd.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._databasePath.Text = ofd.FileName
            if self.require_server:
                return
            self._displayName.Text = ofd.FileName.split('\\')[-1].split('.')[0]

    def OnOk(self, sender, args):
        self.conn_d = {}
        if self.require_server:
            self.conn_d['DataSource'] = self._serverName.Text
        else:
            if self._displayName.Text:
                self.conn_d['DISPLAY_NAME'] = self._displayName.Text
            else:
                self.conn_d['DISPLAY_NAME'] = self._databasePath.Text
        self.conn_d['Database'] = self._databasePath.Text
        self.conn_d['User'] = self._userName.Text
        self.conn_d['Password'] = self._userPass.Text
        self.conn_d['Charset'] = self._charset.Text
        self.conn_d['Role'] = self._role.Text
        self.conn_d['Port'] = str(self._port.Value)
        if self._savePassword.Checked:
            self.conn_d['SAVE_PASS_FLAG'] = '1'
        else:
            self.conn_d['SAVE_PASS_FLAG'] = '0'
        self.DialogResult = Forms.DialogResult.OK
        self.Close()


class SelectItemsForm(Forms.Form):
    def __init__(self, title, items):
        self.Width = 220
        self.Height = 210
        self.Text = title

        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self._list = Forms.ListBox(Left=5, Top=4, Width=200, Height=150)
        self._list.TabIndex = 1
        for s in items:
            self._list.Items.Add(s)
        self._list.SelectionMode = Forms.SelectionMode.MultiExtended
        self.Controls.Add(self._list)

        self.AcceptButton = Forms.Button(
                        Text="&OK", Left=50, Top=155, Size=Size(75,23))
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 2
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(
                        Text="&Cancel", Left=130, Top=155, Size=Size(75, 23))
        self.CancelButton.TabIndex = 3
        self.Controls.Add(self.CancelButton)

    def OnOk(self, sender, args):
        self.DialogResult = Forms.DialogResult.OK
        self.selected = [s for s in self._list.SelectedItems]
        self.Close()


class TableColumnForm(Forms.Form):
    def __init__(self, title, conn):
        self.Width = 425
        self.Height = 230
        self.Text = title

        self.conn = conn

        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog
        self.Controls.Add(
            Forms.Label(Left=5, Top=8, Text="Table", AutoSize=True))
        self._ltTable = Forms.ListBox(Left=5, Top=25, Width=200, Height=150)
        self._ltTable.TabIndex = 1
        for c in self.conn.tables():
            self._ltTable.Items.Add(c['NAME'])
        self._ltTable.SelectedValueChanged += self.OnTableChange
        self.Controls.Add(self._ltTable)

        self.Controls.Add(
            Forms.Label(Left=210, Top=8, Text="Column", AutoSize=True))
        self._ltColumn = Forms.ListBox(Left=210, Top=25, Width=200, Height=150)
        self._ltColumn.TabIndex = 2
        self.Controls.Add(self._ltColumn)

        self.AcceptButton = Forms.Button(
                        Text="&OK", Left=255, Top=176, Size=Size(75,23))
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 3
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(
                        Text="&Cancel", Left=335, Top=176, Size=Size(75, 23))
        self.CancelButton.TabIndex = 4
        self.Controls.Add(self.CancelButton)

    def OnTableChange(self, sender, args):
        self._ltColumn.Items.Clear()
        for c in self.conn.columns(sender.SelectedItem):
            self._ltColumn.Items.Add(c['NAME'])

    def OnOk(self, sender, args):
        self.DialogResult = Forms.DialogResult.OK
        if self._ltTable.SelectedItem:
            self.table_name = self._ltTable.SelectedItem.strip()
        else:
            self.table_name = ''
        if self._ltColumn.SelectedItem:
            self.column_name = self._ltColumn.SelectedItem.strip()
        else:
            self.column_name = ''
        self.Close()


class SqlServerForm(Forms.Form):
    def __init__(self, conn_d):
        self.conn_d = conn_d
        self.Width = 360
        self.Height = 180
        self.Text = 'SQLServer'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=12, Text="Server", AutoSize=True))
        self._server = Forms.TextBox(Left=80, Top=9, Width=250)
        self._server.TabIndex = 1
        self.Controls.Add(self._server)

        self.Controls.Add(
            Forms.Label(Left=12, Top=43, Text="User", AutoSize=True))
        self._user = Forms.TextBox(Left=80, Top=40, Width=250)
        self._user.TabIndex = 2
        self.Controls.Add(self._user)

        self.Controls.Add(
            Forms.Label(Left=12, Top=71, Text="Password", AutoSize=True))
        self._password = Forms.TextBox(Left=80, Top=69, Width=250)
        self._password.PasswordChar = '*'
        self._password.TabIndex = 3
        self.Controls.Add(self._password)

        self._savePassword = Forms.CheckBox(
            Left=30, Top=95, Text="Save Password", AutoSize=True)
        self._savePassword.TabIndex = 4
        self.Controls.Add(self._savePassword)
        
        self.AcceptButton = Forms.Button(Text="&OK", Left=60, Top=121)
        self.AcceptButton.Click += self.OnOk
        self.AcceptButton.TabIndex = 5
        self.Controls.Add(self.AcceptButton)

        self.CancelButton = Forms.Button(Text="&Cancel", Left=220, Top=121)
        self.CancelButton.TabIndex = 6
        self.Controls.Add(self.CancelButton)

        self._server.Text = self.conn_d.get('MSSQL_Server')
        self._user.Text = self.conn_d.get('MSSQL_User')
        self._password.Text = self.conn_d.get('MSSQL_Password')
        f = self.conn_d.get('MSSQL_SAVE_PASS_FLAG')
        if f and int(f):
            self._savePassword.Checked = True

    def OnOk(self, sender, args):
        self.conn_d['MSSQL_PrevUser'] = self.conn_d.get('MSSQL_User')
        self.conn_d['MSSQL_PrevPassword'] = self.conn_d.get('MSSQL_Password')
        self.conn_d['MSSQL_Server'] = self._server.Text
        self.conn_d['MSSQL_User'] = self._user.Text
        self.conn_d['MSSQL_Password'] = self._password.Text
        if self._savePassword.Checked:
            self.conn_d['MSSQL_SAVE_PASS_FLAG'] = '1'
        else:
            self.conn_d['MSSQL_SAVE_PASS_FLAG'] = '0'
        self.DialogResult = Forms.DialogResult.OK

class InOutSqlServerForm(Forms.Form):
    def __init__(self, conn_d, databases, is_import):
        self.conn_d = conn_d
        self.is_import = is_import

        self.Width = 450
        self.Height = 315
        if self.is_import:
            self.Text = 'Import from SQL Server database'
        else:
            self.Text = 'Export to SQL Server database'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=7, Text="MS SQL Server", AutoSize=True))
        self._mssql_server = Forms.TextBox(Left=120, Top=4, Width=250)
        self._mssql_server.TabIndex = 1
        self._mssql_server.ReadOnly = True
        self.Controls.Add(self._mssql_server)

        self.Controls.Add(
            Forms.Label(Left=12, Top=33, Text="MS SQL User", AutoSize=True))
        self._mssql_user = Forms.TextBox(Left=120, Top=30, Width=250)
        self._mssql_user.TabIndex = 2
        self._mssql_user.ReadOnly = True
        self.Controls.Add(self._mssql_user)

        self.Controls.Add(
            Forms.Label(Left=12, Top=58, Text="MS SQL Database", AutoSize=True))
        self._mssql_database = Forms.ComboBox(Left=120, Top=56, Width=250)
        self._mssql_database.TabIndex = 3
        for s in databases:
            self._mssql_database.Items.Add(s)
        self.Controls.Add(self._mssql_database)

        if self.is_import:
            self._populateNode = Forms.CheckBox(
                Left=10, Top=80, Text="Populate node", AutoSize=True)
            self._populateNode.TabIndex = 4
            self.Controls.Add(self._populateNode)

        self._setDefault = Forms.CheckBox(
            Left=140, Top=80, Text="Set default", AutoSize=True)
        self._setDefault.TabIndex = 5
        self.Controls.Add(self._setDefault)

        self._foreignKeys = Forms.CheckBox(
            Left=230, Top=80, Text="Foreign keys", AutoSize=True)
        self._foreignKeys.TabIndex = 6
        self.Controls.Add(self._foreignKeys)

        self._checkConstraints = Forms.CheckBox(
            Left=320, Top=80, Text="Check constraints", AutoSize=True)
        self._checkConstraints.TabIndex = 7
        self.Controls.Add(self._checkConstraints)

        self.Controls.Add(
            Forms.Label(Left=3, Top=113, Text="Display name:", AutoSize=True))
        self._displayName = Forms.TextBox(Left=90, Top=110, Width=340)
        self._displayName.TabIndex = 8
        self.Controls.Add(self._displayName)

        self.Controls.Add(
            Forms.Label(Left=3, Top=144, Text="Database path:", AutoSize=True))
        self._databasePath = Forms.TextBox(Left=90, Top=141, Width=310)
        self._databasePath.TabIndex = 9
        self.Controls.Add(self._databasePath)
        self._pathButton = Forms.Button(
                            Text="...", Left=406, Top=139, Size=Size(24,24))
        self._pathButton.Click += self.OnDbFileOpen
        self._pathButton.TabIndex = 10
        self.Controls.Add(self._pathButton)

        self.Controls.Add(
            Forms.Label(Left=3, Top=177, Text="Username:", AutoSize=True))
        self._userName = Forms.TextBox(Left=90, Top=174, Width=135)
        self._userName.TabIndex = 11
        self.Controls.Add(self._userName)

        self.Controls.Add(
            Forms.Label(Left=235, Top=177, Text="Password:", AutoSize=True))
        self._userPass = Forms.TextBox(Left=295, Top=174, Width=135)
        self._userPass.PasswordChar = '*'
        self._userPass.TabIndex = 12
        self.Controls.Add(self._userPass)

        if self.is_import:
            self._savePassword = Forms.CheckBox(
                Left=300, Top=197, Text="Save Password", AutoSize=True)
            self._savePassword.TabIndex = 13
            self.Controls.Add(self._savePassword)

        self._charsetLabel = Forms.Label(
            Left=3, Top=230, Text="Charset:", AutoSize=True)
        self.Controls.Add(self._charsetLabel)
        self._charset = Forms.ComboBox(Left=90, Top=225, Width=106)
        for name in charset_list():
            self._charset.Items.Add(name)
        self._charset.Text = 'UNICODE_FSS'
        self._charset.TabIndex = 14
        self.Controls.Add(self._charset)

        self.Controls.Add(
            Forms.Label(Left=235, Top=230, Text="Role:", AutoSize=True))
        self._role = Forms.TextBox(Left=295, Top=225, Width=135)
        self._role.TabIndex = 15
        self.Controls.Add(self._role)

        self.AcceptButton = Forms.Button(
                Text="Copy only &Schema", Left=100, Top=255, Size=Size(115,23))
        self.AcceptButton.Click += self.OnCopySchema
        self.AcceptButton.TabIndex = 16
        self.Controls.Add(self.AcceptButton)

        self.CopyDataButton = Forms.Button(
                Text="Copy with &Data", Left=225, Top=255, Size=Size(115,23))
        self.CopyDataButton.Click += self.OnCopyData
        self.CopyDataButton.TabIndex = 17
        self.Controls.Add(self.CopyDataButton)

        self.CancelButton = Forms.Button(
                        Text="&Cancel", Left=348, Top=255, Size=Size(75, 23))
        self.CancelButton.TabIndex = 18
        self.Controls.Add(self.CancelButton)

        self._mssql_server.Text = conn_d.get('MSSQL_Server')
        self._mssql_user.Text = conn_d.get('MSSQL_User')
        if conn_d.get('MSSQL_Database') in databases:
            self._mssql_database.Text = conn_d.get('MSSQL_Database')
        self._displayName.Text = conn_d.get('DISPLAY_NAME')
        self._databasePath.Text = conn_d.get('Database')
        self._userName.Text = conn_d.get('User')
        self._userPass.Text = conn_d.get('Password')
        self._charset.Text = conn_d.get('Charset')
        self._role.Text = conn_d.get('Role')
        if self.is_import:
            self._populateNode.Checked = True
            if int(conn_d.get('SAVE_PASS_FLAG', '0')):
                self._savePassword.Checked = True
            else:
                self._savePassword.Checked = False
        else:
            self._displayName.ReadOnly = True

    def OnDbFileOpen(self, sender, args):
        ofd = Forms.OpenFileDialog()
        ofd.DefaultExt = '.fdb'
        ofd.AddExtension = True
        ofd.CheckFileExists = False
        ofd.Filter = 'Firebird databases (*.fdb)|*.fdb| All files (*.*)|*.*'
        r = ofd.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._databasePath.Text = ofd.FileName
            self._displayName.Text = ofd.FileName.split('\\')[-1].split('.')[0]

    def OnCopySchema(self, sender, args):
        self.need_data_copy = False
        if self.is_import:
            self.populateNode = self._populateNode.Checked
            if self._savePassword.Checked:
                self.conn_d['SAVE_PASS_FLAG'] = '1'
            else:
                self.conn_d['SAVE_PASS_FLAG'] = '0'
        self.setDefault = self._setDefault.Checked
        self.foreignKeys = self._foreignKeys.Checked
        self.checkConstraints = self._checkConstraints.Checked
        self.conn_d['MSSQL_Database'] = self._mssql_database.Text
        if self._displayName.Text:
            self.conn_d['DISPLAY_NAME'] = self._displayName.Text
        else:
            self.conn_d['DISPLAY_NAME'] = self._databasePath.Text
        self.conn_d['Database'] = self._databasePath.Text
        self.conn_d['User'] = self._userName.Text
        self.conn_d['Password'] = self._userPass.Text
        self.conn_d['Charset'] = self._charset.Text
        self.conn_d['Role'] = self._role.Text
        self.DialogResult = Forms.DialogResult.OK
        self.Close()

    def OnCopyData(self, sender, args):
        self.OnCopySchema(sender, args)
        self.need_data_copy = True


class InOutOracleForm(Forms.Form):
    def __init__(self, conn_d, is_import):
        self.conn_d = conn_d
        self.is_import = is_import

        self.Width = 450
        self.Height = 315
        if self.is_import:
            self.Text = 'Import from Oracle database'
        else:
            self.Text = 'Export to Oracle database'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=7, Text="Oracle Server", AutoSize=True))
        self._oracle_server = Forms.TextBox(Left=120, Top=4, Width=250)
        self._oracle_server.TabIndex = 1
        self.Controls.Add(self._oracle_server)

        self.Controls.Add(
            Forms.Label(Left=12, Top=33, Text="Oracle User", AutoSize=True))
        self._oracle_user = Forms.TextBox(Left=120, Top=30, Width=250)
        self._oracle_user.TabIndex = 2
        self.Controls.Add(self._oracle_user)

        self.Controls.Add(
            Forms.Label(Left=12, Top=58, Text="Oracle Password", AutoSize=True))
        self._oracle_password = Forms.TextBox(Left=120, Top=56, Width=135)
        self._oracle_password.PasswordChar = '*'
        self._oracle_password.TabIndex = 3
        self.Controls.Add(self._oracle_password)
        self._saveOraPassword = Forms.CheckBox(
            Left=260, Top=56, Text="Save Password", AutoSize=True)
        self._saveOraPassword.TabIndex = 4
        self.Controls.Add(self._saveOraPassword)

        if self.is_import:
            self._populateNode = Forms.CheckBox(
                Left=10, Top=80, Text="Populate node", AutoSize=True)
            self._populateNode.TabIndex = 5
            self.Controls.Add(self._populateNode)

        self._setDefault = Forms.CheckBox(
            Left=140, Top=80, Text="Set default", AutoSize=True)
        self._setDefault.TabIndex = 6
        self.Controls.Add(self._setDefault)

        self._foreignKeys = Forms.CheckBox(
            Left=230, Top=80, Text="Foreign keys", AutoSize=True)
        self._foreignKeys.TabIndex = 7
        self.Controls.Add(self._foreignKeys)

        self._checkConstraints = Forms.CheckBox(
            Left=320, Top=80, Text="Check constraints", AutoSize=True)
        self._checkConstraints.TabIndex = 8
        self.Controls.Add(self._checkConstraints)

        self.Controls.Add(
            Forms.Label(Left=3, Top=113, Text="Display name:", AutoSize=True))
        self._displayName = Forms.TextBox(Left=90, Top=110, Width=340)
        self._displayName.TabIndex = 9
        self.Controls.Add(self._displayName)

        self.Controls.Add(
            Forms.Label(Left=3, Top=144, Text="Database path:", AutoSize=True))
        self._databasePath = Forms.TextBox(Left=90, Top=141, Width=310)
        self._databasePath.TabIndex = 10
        self.Controls.Add(self._databasePath)
        self._pathButton = Forms.Button(
                            Text="...", Left=406, Top=139, Size=Size(24,24))
        self._pathButton.Click += self.OnDbFileOpen
        self._pathButton.TabIndex = 11
        self.Controls.Add(self._pathButton)

        self.Controls.Add(
            Forms.Label(Left=3, Top=177, Text="Username:", AutoSize=True))
        self._userName = Forms.TextBox(Left=90, Top=174, Width=135)
        self._userName.TabIndex = 12
        self.Controls.Add(self._userName)

        self.Controls.Add(
            Forms.Label(Left=235, Top=177, Text="Password:", AutoSize=True))
        self._userPass = Forms.TextBox(Left=295, Top=174, Width=135)
        self._userPass.PasswordChar = '*'
        self._userPass.TabIndex = 13
        self.Controls.Add(self._userPass)

        if self.is_import:
            self._savePassword = Forms.CheckBox(
                Left=300, Top=197, Text="Save Password", AutoSize=True)
            self._savePassword.TabIndex = 14
            self.Controls.Add(self._savePassword)

        self._charsetLabel = Forms.Label(
            Left=3, Top=230, Text="Charset:", AutoSize=True)
        self.Controls.Add(self._charsetLabel)
        self._charset = Forms.ComboBox(Left=90, Top=225, Width=106)
        for name in charset_list():
            self._charset.Items.Add(name)
        self._charset.Text = 'UNICODE_FSS'
        self._charset.TabIndex = 15
        self.Controls.Add(self._charset)

        self.Controls.Add(
            Forms.Label(Left=235, Top=230, Text="Role:", AutoSize=True))
        self._role = Forms.TextBox(Left=295, Top=225, Width=135)
        self._role.TabIndex = 16
        self.Controls.Add(self._role)

        self.AcceptButton = Forms.Button(
                Text="Copy only &Schema", Left=100, Top=255, Size=Size(115,23))
        self.AcceptButton.Click += self.OnCopySchema
        self.AcceptButton.TabIndex = 17
        self.Controls.Add(self.AcceptButton)

        self.CopyDataButton = Forms.Button(
                Text="Copy with &Data", Left=225, Top=255, Size=Size(115,23))
        self.CopyDataButton.Click += self.OnCopyData
        self.CopyDataButton.TabIndex = 18
        self.Controls.Add(self.CopyDataButton)

        self.CancelButton = Forms.Button(
                        Text="&Cancel", Left=348, Top=255, Size=Size(75, 23))
        self.CancelButton.TabIndex = 19
        self.Controls.Add(self.CancelButton)

        self._oracle_server.Text = conn_d.get('ORACLE_Server')
        self._oracle_user.Text = conn_d.get('ORACLE_User')
        self._oracle_password.Text = conn_d.get('ORACLE_Password')
        if int(conn_d.get('ORACLE_SAVE_PASS_FLAG', '0')):
            self._saveOraPassword.Checked = True
        else:
            self._saveOraPassword.Checked = False
        self._displayName.Text = conn_d.get('DISPLAY_NAME')
        self._databasePath.Text = conn_d.get('Database')
        self._userName.Text = conn_d.get('User')
        self._userPass.Text = conn_d.get('Password')
        self._charset.Text = conn_d.get('Charset')
        self._role.Text = conn_d.get('Role')
        if self.is_import:
            self._populateNode.Checked = True
            if int(conn_d.get('SAVE_PASS_FLAG', '0')):
                self._savePassword.Checked = True
            else:
                self._savePassword.Checked = False
        else:
            self._displayName.ReadOnly = True

    def OnDbFileOpen(self, sender, args):
        ofd = Forms.OpenFileDialog()
        ofd.DefaultExt = '.fdb'
        ofd.AddExtension = True
        ofd.CheckFileExists = False
        ofd.Filter = 'Firebird databases (*.fdb)|*.fdb| All files (*.*)|*.*'
        r = ofd.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._databasePath.Text = ofd.FileName
            self._displayName.Text = ofd.FileName.split('\\')[-1].split('.')[0]

    def OnCopySchema(self, sender, args):
        self.need_data_copy = False
        self.conn_d['ORACLE_Server'] = self._oracle_server.Text
        self.conn_d['ORACLE_User'] = self._oracle_user.Text
        self.conn_d['ORACLE_Password'] = self._oracle_password.Text
        if self._saveOraPassword.Checked:
            self.conn_d['ORACLE_SAVE_PASS_FLAG'] = '1'
        else:
            self.conn_d['ORACLE_SAVE_PASS_FLAG'] = '0'
        if self.is_import:
            self.populateNode = self._populateNode.Checked
            if self._savePassword.Checked:
                self.conn_d['SAVE_PASS_FLAG'] = '1'
            else:
                self.conn_d['SAVE_PASS_FLAG'] = '0'
        self.setDefault = self._setDefault.Checked
        self.foreignKeys = self._foreignKeys.Checked
        self.checkConstraints = self._checkConstraints.Checked
        if self._displayName.Text:
            self.conn_d['DISPLAY_NAME'] = self._displayName.Text
        else:
            self.conn_d['DISPLAY_NAME'] = self._databasePath.Text
        self.conn_d['Database'] = self._databasePath.Text
        self.conn_d['User'] = self._userName.Text
        self.conn_d['Password'] = self._userPass.Text
        self.conn_d['Charset'] = self._charset.Text
        self.conn_d['Role'] = self._role.Text
        self.DialogResult = Forms.DialogResult.OK
        self.Close()

    def OnCopyData(self, sender, args):
        self.OnCopySchema(sender, args)
        self.need_data_copy = True


class InOutSQLiteForm(Forms.Form):
    def __init__(self, conn_d, is_import):
        self.conn_d = conn_d
        self.is_import = is_import

        self.Width = 450
        self.Height = 275
        if self.is_import:
            self.Text = 'Import from SQLite database'
        else:
            self.Text = 'Export to SQLite database'
        self.FormBorderStyle = Forms.FormBorderStyle.FixedDialog

        self.Controls.Add(
            Forms.Label(Left=12, Top=7, Text="SQLite path", AutoSize=True))
        self._sqlite_path = Forms.TextBox(Left=90, Top=4, Width=310)
        self._sqlite_path.TabIndex = 1
        self.Controls.Add(self._sqlite_path)
        self._sqlitePathButton = Forms.Button(
                            Text="...", Left=406, Top=4, Size=Size(24,24))
        self._sqlitePathButton.Click += self.OnSQLiteFileOpen
        self._sqlitePathButton.TabIndex = 2
        self.Controls.Add(self._sqlitePathButton)

        if self.is_import:
            self._populateNode = Forms.CheckBox(
                Left=10, Top=40, Text="Populate node", AutoSize=True)
            self._populateNode.TabIndex = 5
            self.Controls.Add(self._populateNode)

        self._setDefault = Forms.CheckBox(
            Left=140, Top=40, Text="Set default", AutoSize=True)
        self._setDefault.TabIndex = 6
        self.Controls.Add(self._setDefault)

        self._foreignKeys = Forms.CheckBox(
            Left=230, Top=40, Text="Foreign keys", AutoSize=True)
        self._foreignKeys.TabIndex = 7
        self.Controls.Add(self._foreignKeys)

        self.Controls.Add(
            Forms.Label(Left=3, Top=73, Text="Display name:", AutoSize=True))
        self._displayName = Forms.TextBox(Left=90, Top=70, Width=340)
        self._displayName.TabIndex = 9
        self.Controls.Add(self._displayName)

        self.Controls.Add(
            Forms.Label(Left=3, Top=104, Text="Database path:", AutoSize=True))
        self._databasePath = Forms.TextBox(Left=90, Top=101, Width=310)
        self._databasePath.TabIndex = 10
        self.Controls.Add(self._databasePath)
        self._pathButton = Forms.Button(
                            Text="...", Left=406, Top=99, Size=Size(24,24))
        self._pathButton.Click += self.OnDbFileOpen
        self._pathButton.TabIndex = 11
        self.Controls.Add(self._pathButton)

        self.Controls.Add(
            Forms.Label(Left=3, Top=137, Text="Username:", AutoSize=True))
        self._userName = Forms.TextBox(Left=90, Top=134, Width=135)
        self._userName.TabIndex = 12
        self.Controls.Add(self._userName)

        self.Controls.Add(
            Forms.Label(Left=235, Top=137, Text="Password:", AutoSize=True))
        self._userPass = Forms.TextBox(Left=295, Top=134, Width=135)
        self._userPass.PasswordChar = '*'
        self._userPass.TabIndex = 13
        self.Controls.Add(self._userPass)

        if self.is_import:
            self._savePassword = Forms.CheckBox(
                Left=300, Top=157, Text="Save Password", AutoSize=True)
            self._savePassword.TabIndex = 14
            self.Controls.Add(self._savePassword)

        self._charsetLabel = Forms.Label(
            Left=3, Top=190, Text="Charset:", AutoSize=True)
        self.Controls.Add(self._charsetLabel)
        self._charset = Forms.ComboBox(Left=90, Top=185, Width=106)
        for name in charset_list():
            self._charset.Items.Add(name)
        self._charset.Text = 'UNICODE_FSS'
        self._charset.TabIndex = 15
        self.Controls.Add(self._charset)

        self.Controls.Add(
            Forms.Label(Left=235, Top=190, Text="Role:", AutoSize=True))
        self._role = Forms.TextBox(Left=295, Top=185, Width=135)
        self._role.TabIndex = 16
        self.Controls.Add(self._role)

        self.AcceptButton = Forms.Button(
                Text="Copy only &Schema", Left=100, Top=215, Size=Size(115,23))
        self.AcceptButton.Click += self.OnCopySchema
        self.AcceptButton.TabIndex = 17
        self.Controls.Add(self.AcceptButton)

        self.CopyDataButton = Forms.Button(
                Text="Copy with &Data", Left=225, Top=215, Size=Size(115,23))
        self.CopyDataButton.Click += self.OnCopyData
        self.CopyDataButton.TabIndex = 18
        self.Controls.Add(self.CopyDataButton)

        self.CancelButton = Forms.Button(
                        Text="&Cancel", Left=348, Top=215, Size=Size(75, 23))
        self.CancelButton.TabIndex = 19
        self.Controls.Add(self.CancelButton)

        self._sqlite_path.Text = conn_d.get('SQLite_Path')
        self._displayName.Text = conn_d.get('DISPLAY_NAME')
        self._databasePath.Text = conn_d.get('Database')
        self._userName.Text = conn_d.get('User')
        self._userPass.Text = conn_d.get('Password')
        self._charset.Text = conn_d.get('Charset')
        self._role.Text = conn_d.get('Role')
        if self.is_import:
            self._populateNode.Checked = True
            if int(conn_d.get('SAVE_PASS_FLAG', '0')):
                self._savePassword.Checked = True
            else:
                self._savePassword.Checked = False
        else:
            self._displayName.ReadOnly = True

    def OnDbFileOpen(self, sender, args):
        ofd = Forms.OpenFileDialog()
        ofd.DefaultExt = '.fdb'
        ofd.AddExtension = True
        ofd.CheckFileExists = False
        ofd.Filter = 'Firebird databases (*.fdb)|*.fdb| All files (*.*)|*.*'
        r = ofd.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._databasePath.Text = ofd.FileName
            self._displayName.Text = ofd.FileName.split('\\')[-1].split('.')[0]

    def OnSQLiteFileOpen(self, sender, args):
        ofd = Forms.OpenFileDialog()
        ofd.AddExtension = True
        ofd.CheckFileExists = False
        r = ofd.ShowDialog(self)
        if r == Forms.DialogResult.OK:
            self._sqlite_path.Text = ofd.FileName

    def OnCopySchema(self, sender, args):
        self.need_data_copy = False
        self.conn_d['SQLite_Path'] = self._sqlite_path.Text
        if self.is_import:
            self.populateNode = self._populateNode.Checked
            if self._savePassword.Checked:
                self.conn_d['SAVE_PASS_FLAG'] = '1'
            else:
                self.conn_d['SAVE_PASS_FLAG'] = '0'
        self.setDefault = self._setDefault.Checked
        self.foreignKeys = self._foreignKeys.Checked
        if self._displayName.Text:
            self.conn_d['DISPLAY_NAME'] = self._displayName.Text
        else:
            self.conn_d['DISPLAY_NAME'] = self._databasePath.Text
        self.conn_d['Database'] = self._databasePath.Text
        self.conn_d['User'] = self._userName.Text
        self.conn_d['Password'] = self._userPass.Text
        self.conn_d['Charset'] = self._charset.Text
        self.conn_d['Role'] = self._role.Text
        self.DialogResult = Forms.DialogResult.OK
        self.Close()

    def OnCopyData(self, sender, args):
        self.OnCopySchema(sender, args)
        self.need_data_copy = True
