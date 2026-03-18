# Wiring    

## Camera  

Replace the stock cable with the new one, and connect into the RP Pi camera slot.  

## Display ST7789 2.8" TFT  

VCC -> 3.3V  
GND -> GND  
SCK -> GPIO 11  
MOSI -> GPIO 10  
CS -> GPIO 8  
DC -> GPIO 25  
RST -> GPIO 27  
BL -> GPIO 24  


## GPS NEO-8M  

VCC -> 3.3V  
GND -> GND  
TX -> GPIO 15  
RX -> GPIO 14  


## INMP441 Microphone  

VDD -> 3.3V  
GND -> GND  
SCK -> GPIO 18  
WS -> GPIO 19  
SD -> GPIO 20  
L/R -> GND  

## 7× Tact Switches  

Button 1 -> GPIO 23 / GND    // Start / Stop recording  
Button 2 -> GPIO 22 / GND    // Toggle display backlight (camera keeps running)  
Button 3 -> GPIO 3 / GND     // Save recording + safe shutdown  
Button 4 -> GPIO 5 / GND     // Open / close playback  
Button 5 -> GPIO 6 / GND     // Back in playback  
Button 6 -> GPIO 12 / GND    // stop/play plaback  
Button 7 -> GPIO 13 / GND    // Forward in playback  

On each 4-pin tact switch connect one side pair to GPIO, other side to shared GND.   

## SD Card  
Put the SD Card into the RP Pi  

## Screws  
Screw the screws into the correct hole, M2x4mm is to hold camera and RP Pi, the M2x16mm is to hold the case together.  




<details>
  <summary>For Future</summary>
  
  ## here you can see wiring for what i plan to add in the future  


## UPS HAT  
Slap it right on top of the RP Pi, put both batteries in it. 


## Active Buzzer/Speaker  
VCC -> 3.3V  
I/O -> GPIO 17  
GND -> GND  


  
</details>
