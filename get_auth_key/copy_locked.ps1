param (
  [string]$sourcePath = "C:\Program Files\HoYoPlay\games\Genshin Impact game\GenshinImpact_Data\webCaches\2.37.0.0\Cache\Cache_Data\data_2",
  [string]$destinationPath = "$env:TEMP\data2_copy"
)

Add-Type -TypeDefinition @"
using System;
using System.IO;
using System.Runtime.InteropServices;

public class LockedFileCopy {
    public static void CopyLockedFile(string sourcePath, string destinationPath) {
        using (var input = new FileStream(sourcePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
        using (var output = new FileStream(destinationPath, FileMode.Create, FileAccess.Write)) {
            input.CopyTo(output);
        }
    }
}
"@

[LockedFileCopy]::CopyLockedFile($sourcePath, $destinationPath)
