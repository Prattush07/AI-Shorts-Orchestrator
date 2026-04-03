$body = @{url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/projects" -Method Post -Body $body -ContentType "application/json"
