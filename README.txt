About FbConsole

  FbConsole is management tool for Firebird (http://www.firebirdsql.org/),
like IBConsole for InterBase or pgAdmin for PostgreSQL. 
But it works only MS Windows variant, because it is .NET Forms application 
written by IronPython.

- Requirement
  [.NET Framework 2.0]
  http://www.microsoft.com/downloads/details.aspx?FamilyID=0856EACB-4362-4B0D-8EDD-AAB15C5E04F5

  [Firebird .Net Data Provider] 2.0 or later
  http://www.firebirdsql.org/index.php?op=files&id=netprovider
    Install "%ProgamFiles%\FirebirdClient 2.0" directory or copy DLL's to 
    FbConsole directory.

  [IronPython] 1.x or 2.x
  http://www.codeplex.com/IronPython

  [Microsoft SQL Server 2005 Management Objects Collection] Optional
    If you want to import or export data via SQL Server.
  http://www.microsoft.com/downloads/details.aspx?FamilyID=50b97994-8453-4998-8226-fa42ec403d17

  [System.Data.SQLite] Optional
    If you want to import or export data via SQLite.
  http://sqlite.phxsoftware.com/


- How to start
    Set PATH environment variable to IronPython installed directory 
  and execute as 
  > ipyw.exe FbConsole.py
  on command console(or create shortcut and kick it).

  (Unofficial ;-)
  > ipyw.exe FbSqlForm.py
  Then start isql console.
  > ipyw.exe SQLiteEdit.py
  Then start SQLite data editor.

- License
    Python codes are under FreeBSD License. See source header.
  Icon images are taken from FlameRobin project (http://www.flamerobin.org/).
  So some images (from Ximian project) under LGPL and others (from FlameRobin 
  project) are under BSD-like Expat license.  See res/COPYING file.
