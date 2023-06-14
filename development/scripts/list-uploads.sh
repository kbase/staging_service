#
# A handy script to display the contents of the data directory in a 
# terminal window, refreshing every 0.5 seconds and excluding 
# any macOS .DS_Store Desktop Services files.
#
while :
do
    clear
    find data -type f \( ! -name ".DS_Store" \) -ls 
    sleep 0.5
done