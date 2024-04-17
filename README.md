## Usage:
Just copy without re-encoding:  
`python videco.py -i <dir> -o <dir>`

Use the nvidia h265 codec with optimal parameters:  
`python videco.py -i <dir> -o <dir> -v "-c:v hevc_nvenc -preset medium -cq 30"`
