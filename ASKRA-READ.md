# Update 2nd of March 2024:
- after a bit more work, I managed to used dlms-cosem to feed in some frame data and thus use a more high level code to decypher the payload.

I leave here the original procedure for reference:

# Dummy parser for P1 on ASKRA AM 550, installed by SIE - Lausanne, Switzerland

I've tried for a quite a while to decode the data coming from the P1 port of my ASKRA AM 550 installed by the SIE Lausanne.

Amongst others, I've tried

- [DSMR PARSER](https://github.com/ndokter/dsmr_parser)
- [Gurux.DLMS.Python](https://github.com/Gurux/Gurux.DLMS.Python)
- iec62056-21
- [dlms-cosem](https://github.com/u9n/dlms-cosem)
- [SlimmeLezer](https://www.zuidwijk.com/product/slimmelezer/)
- and others...

Thanks to [this reply](https://github.com/u9n/dlms-cosem/issues/71#issuecomment-1898325988) and its link to (https://hanporten.se/norska/protokollet/) I've been pointed in the right direction.

### Disclaimer

Rather than put here my own code and pretend it just works, I'll detail the steps I've taken to decrypt this mess. I'm sure the things I do look pathetic to anyone with a tiny bit of prior knowledge on how DLMS/HDLC and the like are structured but, as said before, none of the complex and very well written package I've found on the subject happened to work for my case. Anyway, comment are welcome.

## Steps to read the data

One first needs to read the binary data and dump them in a terminal. `pyserial` is really easy for that.

One gets something like this (the XXXX are just meter serial numbers.)
``````
7ea8a4cf0223039996e6e7000f001851de0c07e802010408141900ffc400021002020906XXXXXXXXXXXXXXXXXXXX02020906XXXXXXXXXXXXXXXXXXXX020309060100010700ff060000013802020f00161b020309060100020700ff060000000002020f00161b020309060100010800ff0600554fdc02020f00161e020309060100020800ff06007547fa02020f00161e02030906010020074ca97e7ea8a4cf022303999600ff1208db02020fff1623020309060100340700ff1208e502020fff1623020309060100480700ff1208d002020fff16230203090601001f0700ff12004002020ffe1621020309060100330700ff12002c02020ffe1621020309060100470700ff12007602020ffe1621020309060100010801ff060026cc7f02020f00161e020309060100010802ff06002e835d02020f00161e0203090601002d7a7e7ea02ecf022313bd61020801ff060054ed4502020f00161e020309060100020802ff0600205ab502020f00161e0c3c7e

7ea8a4cf0223039996e6e7000f001851df0c07e802010408141e00ffc400021002020906XXXXXXXXXXXXXXXXXXXX02020906XXXXXXXXXXXXXXXXXXXX020309060100010700ff060000013c02020f00161b020309060100020700ff060000000002020f00161b020309060100010800ff0600554fdc02020f00161e020309060100020800ff06007547fa02020f00161e0203090601002007a55f7e7ea8a4cf022303999600ff1208da02020fff1623020309060100340700ff1208e502020fff1623020309060100480700ff1208d002020fff16230203090601001f0700ff12004002020ffe1621020309060100330700ff12002c02020ffe1621020309060100470700ff12007902020ffe1621020309060100010801ff060026cc7f02020f00161e020309060100010802ff06002e835d02020f00161e020309060100f1fd7e7ea02ecf022313bd61020801ff060054ed4502020f00161e020309060100020802ff0600205ab502020f00161e0c3c7e
``````

The frames are surrouned by the byte '7e' So each data pack is actually three frames here. So the first data pack above should be read:

```
7ea8a4cf0223039996e6e7000f001851de0c07e802010408141900ffc400021002020906XXXXXXXXXXXXXXXXXXXX02020906XXXXXXXXXXXXXXXXXXXX020309060100010700ff060000013802020f00161b020309060100020700ff060000000002020f00161b020309060100010800ff0600554fdc02020f00161e020309060100020800ff06007547fa02020f00161e02030906010020074ca97e

7ea8a4cf022303999600ff1208db02020fff1623020309060100340700ff1208e502020fff1623020309060100480700ff1208d002020fff16230203090601001f0700ff12004002020ffe1621020309060100330700ff12002c02020ffe1621020309060100470700ff12007602020ffe1621020309060100010801ff060026cc7f02020f00161e020309060100010802ff06002e835d02020f00161e0203090601002d7a7e

7ea02ecf022313bd61020801ff060054ed4502020f00161e020309060100020802ff0600205ab502020f00161e0c3c7e
```

From here, one take the list of OBIS codes and look at it in the data (one can find the OBIS code in the datasheet of the smartmeter. Full of typo obviously... but still some are correct ant the other can be guessed). For example Obis 1-0:72.7.0 from the counter translates to '0100480700' (hex representation of the bytes), which can be found in the raw data. Note that at this point, some of the obis cannot be found because the payload are splitted.

This step allows to understand how the data are structured. Copy pasting another frame of data which is not here above and splitting it around these patterns, one gets:

```
7e a8a4 cf 0223 03 9996 e6e7 
    000f 0017 c461 0c07 e801 1204 1323 2d00 ffc4 0002 10   # no idea what this is. Time, date, frame length ?
    
    0202 0906 0000600100 ff 09 XXXXXXXXXXXXXXXXXX          # serial number from askra
    0202 0906 0000600101 ff 09 XXXXXXXXXXXXXXXX            # serial number for one smartmeter
    0203 0906 0100010700 ff 06 00000489 02020f 00 16 1b    # puissance instantannée à l'import
    0203 0906 0100020700 ff 06 00000000 02020f 00 16 1b    # puissance instantannée à l'export
              |             |  |        |      |     |- 0x1b = 27 = Watts (according to OBIS blue book)
              |             |  |        |      | scale factor of 10^0
              |             |  |        |- seems to be a separator...
              |             |  |- actual power value
              |             |- seems to tell whether the value is encoded on two or three bytes. Not sure though.
              |----- OBIS codes                               
    0203 0906 0100010800 ff 06 00517bf7 02020f 00 16 1e    # Total Active energy import +A (look at obis codes to know the label)
    0203 0906 0100020800 ff 06 0073b484 02020f 00 16 1e    # Total Active energy export +A
                                                     |- 0x1e = 30 = Wh
    0203 0906 0100200700 ff 12 08e4 02020f ff 16 23        # 1-0:32.7.0: Tension instantannée L1
    0203 0906 0100340700 ff 12 08e7 02020f ff 16 23        # 1-0:52.7.0: Tension instantannée L2
    0203 0906 0100480700 ff 12 08e4 02020f ff 16 23        # 1-0:72.7.0: Tension instantannée L3
                               |           |     |- 0x23 = 35 = Volts
                               |           |- ff is -1 as signed int so factor 10^(-1)
                               |- 0x84e4 = 2276 so factor 10^(-1) is required to make 227.6 Volts.

    0203 0906 01001f07                                    # this line is truncated and this is normal.
7aea 7e
|    |- HDLC end of frame
|- two bytes or CRC check


7e a8a4 cf 0223 03 9996    
                      # the payload just continues after the "header" bytes
                      00 ff 12 003f 02020f fe 16 21        # 1-0:31.7.0: courant instantané 1
    0203 0906 0100330700 ff 12 014d 02020f fe 16 21        # 1-0:51.7.0: courant instantané 2
    0203 0906 0100470700 ff 12 00b0 02020f fe 16 21        # 1-0:71.7.0: courant instantané 3
                               |           |     |- 0x21 = 33 = Ampere
                               |           |- fe is -2 as signed int
                               |- 0x14d = 333*10^(-3) = 3.33 A

                                
    0203 0906 0100010801 ff 06 002542d1 02020f 00 16 1e    # 1-0:1.8.1:  Energie active import +A tarif 1 (Heures Pleines)
    0203 0906 0100010802 ff 06 002c3926 02020f 00 16 1e    # 1-0:1.8.2:  Energie active import +A tarif 2 (Heures Creuses)
    0203 0906 0100                                         # this line is truncated and this is normal.
0026 7e
|    |- HDLC end of frame
|- two bytes or CRC check

7e a02e cf 0223 13 bd61                                     # after some header, the data just continue.
                  020801ff 06 0053aebc 02020f 00 16 1e      # 1-0:2.8.1:  Energie active export -A tarif 1 (Heures Pleines)
    0203 0906 0100020802ff 06 002005c8 02020f 00 16 1e      # 1-0:2.8.2:  Energie active export -A tarif 2 (Heures Creuses)  
7be2 7e
```

So basically, what the script does is simply gathering the payload together and then do some regex matching to find the obis codes position, finally it reads the values and prints it.
