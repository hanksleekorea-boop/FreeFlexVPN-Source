$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $scriptDir = Join-Path (Get-Location) 'freekoreavpn\20_SRC\docgen'
}
else {
    $scriptDir = $PSScriptRoot
}
$projectRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$sourcePath = Join-Path $projectRoot '60_OUTPUTS\archive_2026-07-31\legacy_docs\Free_Korea_VPN_사업기획서.docx'
$outputPath = Join-Path $projectRoot '60_OUTPUTS\FreeFlexVPN_사업계획서_v1.0_2026-07-31.docx'

Write-Output "STEP source: $sourcePath"

if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Source document not found: $sourcePath"
}

Copy-Item -LiteralPath $sourcePath -Destination $outputPath -Force
Write-Output "STEP copied: $outputPath"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$replacements = [ordered]@{
    'Free Korea VPN' = 'FreeFlexVPN'
    'FreeKoreaVPN' = 'FreeFlexVPN'
    '사업기획서' = '사업계획서'
    '12. 의사결정이 필요한 항목' = '12. 확정사항과 추가 의사결정'
    '2026년 7월 30일' = '2026년 7월 31일'
    'FreeFlexVPN (가칭)' = 'FreeFlexVPN'

    '회원 1인당 월 2GB를 무료로 제공하고' = '회원 1인당 월 1GB를 무료로 제공하고'
    '무료 제공량: 1인 월 2GB' = '무료 제공량: 1인 월 1GB'
    '가입하면 매달 2GB가 무료이고, 더 필요하면 커피 한 잔 값으로 데이터를 충전해 쓰는 VPN.' = '가입하면 매달 1GB가 무료이고, 더 필요할 때 필요한 만큼만 충전하며, 충전 용량은 만료 없이 남는 VPN.'
    '2GB (매월 리셋, 이월 없음)' = '1GB (매월 리셋, 이월 없음)'
    '무료 2GB · 일본 노드 1대 · 초대제 100명' = '무료 1GB · 일본 노드 1대 · 초대제 100명'
    '다중계정으로 2GB 상한 무력화' = '다중계정으로 1GB 상한 무력화'
    '1인 2GB 상한' = '1인 1GB 상한'
    '월 2GB 상시' = '월 1GB 상시'
    '무료 2GB + 충전식 종량제' = '무료 1GB + 충전식 종량제'
    '월 2GB 무료가 이 층의 진입 장벽을 0으로 만든다.' = '월 1GB 무료가 이 층의 진입 장벽을 0으로 만들고, 필요가 생긴 순간 자연스럽게 충전으로 이어지게 한다.'

    '월 데이터 사용량이 20GB 이하인 라이트 사용자 — 종량제가 1개월권($12.95 = 19,040원) 대비 48GB까지 유리하다.' = 'VPN이 상시가 아니라 상황별 도구인 라이트 사용자 — 해외여행, 공용 Wi-Fi, 지역 제한 콘텐츠 등 필요할 때만 접속하며 월 사용량이 대체로 10GB 이하인 층.'
    '특정 시점에만 필요한 사용자 — 해외여행, 스포츠 중계, 지역 제한 콘텐츠 등. 1일권·주말권 수요.' = '특정 시점에만 필요한 사용자 — 해외여행, 공용 Wi-Fi, 출장, 스포츠 중계, 지역 제한 콘텐츠 등. 필요할 때만 충전하는 수요.'
    '타깃은 "월 20GB 이하 사용자 + 선불·자동갱신을 거부하는 사용자"로 명확히 좁힌다.' = '타깃은 "가끔 VPN이 필요한 라이트 사용자 + 선불 장기약정·자동갱신을 거부하는 사용자"로 명확히 좁힌다.'
    '무료 상한 — 2GB(원가 최소)인가 5GB(체감 우위)인가. 5GB로 올리면 무료 단계 월 비용이 약 1.6배가 된다.' = '무료 상한(확정) — 월 1GB로 운영한다. 라이트 사용자의 진입 장벽은 낮추되 무료 트래픽 비용과 다중계정 남용을 제한하고, 추가 수요는 무기한 충전 용량으로 전환한다.'

    '연간 합계: 1년차 590,269원 · 2년차 766,410원 · 3년차 942,551원 (3년 누적 약 230만원). 회원이 36배 늘 때 비용은 1.9배만 증가한다.' = '연간 합계: 1년차 563,170원 · 2년차 603,818원 · 3년차 725,762원 (3년 누적 약 189만원). 회원이 36배 늘 때 비용은 약 1.3배만 증가한다.'
}

$freeGrowthReplacements = [ordered]@{
    '2.0TB' = '1.0TB'
    '12.0TB' = '6.0TB'
    '22.0TB' = '11.0TB'
    '48.0TB' = '24.0TB'
    '72.0TB' = '36.0TB'
    '19Mbps' = '9Mbps'
    '111Mbps' = '56Mbps'
    '204Mbps' = '102Mbps'
    '444Mbps' = '222Mbps'
    '667Mbps' = '333Mbps'
    '2대' = '1대'
    '3대' = '2대'
    '4대' = '2대'
    '60,480원' = '46,931원'
    '74,029원' = '60,480원'
    '87,579원' = '60,480원'
    '5.5원' = '4.3원'
    '3.1원' = '2.5원'
    '2.4원' = '1.7원'
}

$revenueReplacements = [ordered]@{
    '24TB' = '14TB'
    '28TB' = '18TB'
    '36TB' = '26TB'
    '52TB' = '42TB'
    '70,591원' = '41,160원'
    '83,336원' = '52,920원'
    '105,886원' = '76,440원'
    '152,947원' = '123,480원'
    '88만원' = '91만원'
    '212만원' = '215만원'
    '431만원' = '434만원'
    '889만원' = '892만원'
    '74%' = '76%'
    '85%' = '86%'
    '90%' = '91%'
}

function Replace-InTextNodeXml([string]$xmlText) {
    foreach ($pair in $replacements.GetEnumerator()) {
        if ($pair.Key.Contains('|')) {
            continue
        }
        $xmlText = $xmlText.Replace($pair.Key, $pair.Value)
    }
    return $xmlText
}

$archive = [System.IO.Compression.ZipFile]::Open($outputPath, [System.IO.Compression.ZipArchiveMode]::Update)
Write-Output 'STEP archive opened'
try {
    $xmlEntries = @($archive.Entries | Where-Object {
        $_.FullName -eq 'word/document.xml' -or
        $_.FullName -like 'word/header*.xml' -or
        $_.FullName -like 'word/footer*.xml' -or
        $_.FullName -eq 'docProps/core.xml'
    })

    foreach ($entry in $xmlEntries) {
        Write-Output "STEP entry: $($entry.FullName)"
        $reader = [System.IO.StreamReader]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false), $true)
        try {
            $xmlText = $reader.ReadToEnd()
        }
        finally {
            $reader.Dispose()
        }

        $xmlText = Replace-InTextNodeXml $xmlText

        if ($entry.FullName -eq 'word/document.xml') {
            $docXml = [xml]$xmlText
            $ns = [System.Xml.XmlNamespaceManager]::new($docXml.NameTable)
            $ns.AddNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

            foreach ($table in $docXml.SelectNodes('//w:tbl', $ns)) {
                $tableText = ($table.SelectNodes('.//w:t', $ns) | ForEach-Object { $_.'#text' }) -join ''
                $tableMap = $null
                if ($tableText -like '*시점*회원*트래픽*피크*노드*월 비용*1인당*') {
                    $tableMap = $freeGrowthReplacements
                }
                elseif ($tableText -like '*유료 전환율*결제 인원*ARPU*월 매출*트래픽*인프라*월 이익*이익률*') {
                    $tableMap = $revenueReplacements
                }
                if ($null -ne $tableMap) {
                    foreach ($node in $table.SelectNodes('.//w:t', $ns)) {
                        foreach ($pair in $tableMap.GetEnumerator()) {
                            if ($node.'#text' -eq $pair.Key) {
                                $node.'#text' = $pair.Value
                                break
                            }
                        }
                    }
                }

                $rows = @($table.SelectNodes('./w:tr', $ns))
                for ($rowIndex = 0; $rowIndex -lt $rows.Count; $rowIndex++) {
                    $row = $rows[$rowIndex]
                    $rowProperties = $row.SelectSingleNode('./w:trPr', $ns)
                    if ($null -eq $rowProperties) {
                        $rowProperties = $docXml.CreateElement('w', 'trPr', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
                        [void]$row.PrependChild($rowProperties)
                    }
                    foreach ($headerNode in @($rowProperties.SelectNodes('./w:tblHeader', $ns))) {
                        [void]$rowProperties.RemoveChild($headerNode)
                    }
                    if ($rowIndex -eq 0) {
                        $headerNode = $docXml.CreateElement('w', 'tblHeader', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
                        [void]$headerNode.SetAttribute('val', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'true')
                        [void]$rowProperties.AppendChild($headerNode)
                    }
                }
            }

            $xmlText = $docXml.OuterXml
        }

        $entryName = $entry.FullName
        $entry.Delete()
        $newEntry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
        $writer = [System.IO.StreamWriter]::new($newEntry.Open(), [System.Text.UTF8Encoding]::new($false))
        try {
            $writer.Write($xmlText)
        }
        finally {
            $writer.Dispose()
        }
        Write-Output "STEP entry complete: $entryName"
    }
}
finally {
    $archive.Dispose()
}
Write-Output 'STEP archive closed'

$hash = Get-FileHash -LiteralPath $outputPath -Algorithm SHA256
[pscustomobject]@{
    Output = $outputPath
    Bytes = (Get-Item -LiteralPath $outputPath).Length
    SHA256 = $hash.Hash
} | Format-List
