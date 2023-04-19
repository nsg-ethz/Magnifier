# converts collected sFlow samples in an easy to process format
#
# usage: ./sflow_conversion.sh <name of corresponding nfcapd file>

nfdump -r "$1" -o "fmt:%tsr,%ter,%trr,%td,%pr,%sa,%da,%sp,%dp,%ipkt,%opkt,%ibyt,%obyt,%fl,%exp,%ra,%in,%out" > sflow/dummy.csv
