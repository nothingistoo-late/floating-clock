param()
$player = New-Object -ComObject WMPlayer.OCX
$player.settings.autoStart = $true
$player.settings.volume = 50

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::WriteLine("READY")

while ($line = [Console]::ReadLine()) {
    if ($null -eq $line -or $line -eq "quit") {
        break
    }
    $parts = $line -split " ", 2
    $cmd = $parts[0]
    $arg = if ($parts.Length -gt 1) { $parts[1] } else { "" }

    switch ($cmd) {
        "play" {
            try {
                $player.URL = $arg
                $player.controls.play()
                [Console]::WriteLine("OK_PLAYING")
            } catch {
                [Console]::WriteLine("ERROR_PLAY")
            }
        }
        "stop" {
            try {
                $player.controls.stop()
                $player.close()
                [Console]::WriteLine("OK_STOPPED")
            } catch {
                [Console]::WriteLine("ERROR_STOP")
            }
        }
        "pause" {
            try {
                $player.controls.pause()
                [Console]::WriteLine("OK_PAUSED")
            } catch {
                [Console]::WriteLine("ERROR_PAUSE")
            }
        }
        "resume" {
            try {
                $player.controls.play()
                [Console]::WriteLine("OK_RESUMED")
            } catch {
                [Console]::WriteLine("ERROR_RESUME")
            }
        }
        "volume" {
            try {
                $vol = [int]$arg
                $player.settings.volume = [Math]::Max(0, [Math]::Min(100, $vol))
                [Console]::WriteLine("OK_VOLUME")
            } catch {
                [Console]::WriteLine("ERROR_VOLUME")
            }
        }
        "loop" {
            try {
                $isLoop = ($arg -eq "1" -or $arg -eq "true")
                $player.settings.setMode("loop", $isLoop)
                [Console]::WriteLine("OK_LOOP")
            } catch {
                [Console]::WriteLine("ERROR_LOOP")
            }
        }
        "status" {
            $st = $player.playState
            [Console]::WriteLine("STATUS_$st")
        }
    }
}
$player.close()
