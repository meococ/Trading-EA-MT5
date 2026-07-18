[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$secure = Read-Host 'Paste Databento API key (input is hidden)' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ($plain -notmatch '^db-[A-Za-z0-9_-]{29}$') {
        throw 'Unexpected key format. Expected a 32-character Databento key beginning with db-.'
    }
    [Environment]::SetEnvironmentVariable('DATABENTO_API_KEY', $plain, 'User')
    Write-Host 'DATABENTO_API_KEY saved to the Windows user environment.'
    Write-Host 'The key was not written to the repository or printed.'
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plain = $null
    $secure.Dispose()
}
