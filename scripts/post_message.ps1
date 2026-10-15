param(
    [Parameter(Mandatory = $true)] [string] $Token,
    [string] $Url = "http://127.0.0.1:8000",
    [string] $ClanId = "demo-clan",
    [string] $Sender = "测试成员",
    [Parameter(Mandatory = $true)] [string] $Content
)

$body = @{
    clan_id = $ClanId
    sender = $Sender
    content = $Content
    source = "manual_test"
    source_message_id = [guid]::NewGuid().ToString()
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$($Url.TrimEnd('/'))/api/v1/messages" `
    -Headers @{ "X-Collector-Token" = $Token } `
    -ContentType "application/json" `
    -Body $body

