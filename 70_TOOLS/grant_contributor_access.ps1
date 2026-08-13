[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$')]
    [string]$GitHubUsername,

    [ValidatePattern('^(user|group|serviceAccount):[^\s]+$')]
    [string]$GooglePrincipal = '',

    [string]$Repository = 'hanksleekorea-boop/FreeFlexVPN-Source',
    [string]$Bucket = 'freeflexvpn-live-20260810-a31d7f',
    [switch]$Execute
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$gh = Get-Command gh -ErrorAction SilentlyContinue
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
$plan = [ordered]@{
    schema = 'freeflexvpn-contributor-access/v1'
    repository = $Repository
    github_username = $GitHubUsername
    github_permission = 'push'
    bucket = $Bucket
    google_principal = $(if ($GooglePrincipal) { $GooglePrincipal } else { $null })
    google_role = $(if ($GooglePrincipal) { 'roles/storage.objectAdmin' } else { $null })
    anonymous_write = $false
    shared_token = $false
    execute = [bool]$Execute
}

if (-not $Execute) {
    $plan.status = 'PLAN_ONLY'
    $plan.next = 'Re-run with -Execute after confirming both identities.'
    $plan | ConvertTo-Json -Depth 4
    exit 0
}

if (-not $gh) { throw 'GitHub CLI(gh)가 필요합니다.' }
& $gh.Source auth status | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI 인증이 필요합니다.' }

if ($PSCmdlet.ShouldProcess("$Repository collaborator $GitHubUsername", 'Grant GitHub push permission')) {
    & $gh.Source api -X PUT "repos/$Repository/collaborators/$GitHubUsername" -f permission=push | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'GitHub 협업자 초대에 실패했습니다.' }
}

if ($GooglePrincipal) {
    if (-not $gcloud) { throw '사이트 버킷 권한에는 Google Cloud CLI(gcloud)가 필요합니다.' }
    if ($PSCmdlet.ShouldProcess("gs://$Bucket $GooglePrincipal", 'Grant bucket-scoped object editor permission')) {
        & $gcloud.Source storage buckets add-iam-policy-binding "gs://$Bucket" --member=$GooglePrincipal --role='roles/storage.objectAdmin' --quiet | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Google Cloud Storage 버킷 편집 권한 부여에 실패했습니다.' }
    }
}

$plan.status = 'REQUESTED_AND_READBACK_REQUIRED'
$plan.next = 'The invited GitHub account must accept the invitation; read back GitHub and bucket IAM before claiming access complete.'
$plan | ConvertTo-Json -Depth 4
