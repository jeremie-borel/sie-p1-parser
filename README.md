# Integration of ASKRA AM 550 P1 Port and SolarEdge Inverter with InfluxDB and EVCC

Starting from a tiny proof of concept to read the P1 port from ASKRA AM550 installed by Romande Energie (Lausanne, Switzerland), this project has now evolved to a multi-process, reading the data from the P1 and the SolarEdge web API to feed data into InfluxDB and provide a web server with key values to feed EVCC (evcc.io).

Should one be interesed in the P1 reading, look at the ASKRA-READ.md file and the p1daemon/workers/sie.py source code.


