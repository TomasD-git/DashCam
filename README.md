# DashCam  

<img width="464" height="300" alt="Screenshot 2026-03-18 174442" src="https://github.com/user-attachments/assets/33ae5e6f-092a-4b74-9f8c-cbe74205fd66" />

### DashCam is my project for stasis, it has a lot of capabilities such as, it can precisely track location, speed and time also has a great RP Pi camera V2, has 7 buttons to control playback on 2.8INCH screen, all powered by RP Pi 2 Zero W  

**How it works?**  
It has camera and microphone which record audio and video, saves to Micro Sd Card.      
Has screen where you can view playback, you can even control it with 7 buttons.  

















<details>
  <summary>Click me to see BOM</summary>

| Name | Purpose | Cost Per Item (USD) | Quantity | Total (USD) | Link | Distributor |
|------|---------|-------------------|---------|------------|------|------------|
| 2.8 TFT ST7789 | to see playback on | 7.50 | 1 | 7.50 | [Link](https://www.aliexpress.com/item/1005007346338083.html) | aliexpress |
| 32GB Micro SD Card + reader | To store the firmware and OS on + reader to actually flash it | 11.00 | 1 | 11.00 | [Link](https://www.aliexpress.com/item/1005007501610476.html) | aliexpress |
| isolation tape | NEEDED because there are only 2, 3.3V on the RP Pi so I will need to tape together more cables to use more things out of 1, 3.3V | 4.38 | 1 | 4.38 | [Link](https://www.alza.cz/hobby/yato-paska-izolacni-250-19-mm20-m-cerna-d7772288.htm) | alza |
| Micro USB to USB A | to power the RP Pi | 4.38 | 1 | 4.38 | [Link](https://www.alza.cz/vention-usb-2-0-to-micro-usb-2a-cable-0-5m-black-d7375191.htm) | alza |
| Camera wire to RP Pi 2 zero | the cable that comes with the stock camera isn't connectable to the RP Pi so this one fixes it | 0.61 | 1 | 0.61 | [Link](https://www.aliexpress.com/item/32901067740.html) | aliexpress |
| M-M jumper wires | to connect everything together | 1.00 | 1 | 1.00 | [Link](https://www.aliexpress.com/item/32921454163.html) | aliexpress |
| M-F jumper wires | to connect everything together | 1.00 | 1 | 1.00 | [Link](https://www.aliexpress.com/item/32921454163.html) | aliexpress |
| F-F jumper wires | to connect everything together | 1.00 | 1 | 1.00 | [Link](https://www.aliexpress.com/item/32921454163.html) | aliexpress |
| microphone module, INMP441 | to hear sound with the recording | 2.50 | 1 | 2.50 | [Link](https://www.aliexpress.com/item/1005009182912928.html) | aliexpress |
| Active buzzer | to hear sound | 3.00 | 1 | 3.00 | [Link](https://www.aliexpress.com/item/1005009511933104.html) | aliexpress |
| NEO-8M with antenna | GPS so the microcontroller can see time, location and speed | 10.00 | 1 | 10.00 | [Link](https://www.aliexpress.com/item/1005006323393609.html) | aliexpress |
| 6x6x9.5 tact switches | to control the playback and recording | 1.00 | 1 | 1.00 | [Link](https://www.aliexpress.com/item/4000206046150.html) | aliexpress |
| Raspberry Pi Camera V2 | so it can see what's happening | 24.00 | 1 | 24.00 | [Link](https://www.aliexpress.com/item/1005006000564400.html) | aliexpress |
| Raspberry Pi Zero 2 W | brain of the whole project | 27.00 | 1 | 27.00 | [Link](https://www.aliexpress.com/item/1005008147614202.html) | aliexpress |
| M2x4mm, M2x16m | to hold all parts and the case together | 1.00 | 2 | 2.00 | [Link](https://www.aliexpress.com/item/1005008269323359.html) | aliexpress |

</details>
<details>
  <summary>Disassembly</summary>
  
<img width="864" height="600" alt="Screenshot 2026-03-18 174442" src="https://github.com/user-attachments/assets/f7bc1b5f-f299-4e1c-89ae-05e89ee51622" />
<img width="854" height="714" alt="Screenshot 2026-03-18 174456" src="https://github.com/user-attachments/assets/98304a50-a677-4c94-aa60-1f81e5cb0b6d" />
<img width="882" height="704" alt="Screenshot 2026-03-18 174512" src="https://github.com/user-attachments/assets/ae941128-b25b-444a-8a29-7adc640de850" />
<img width="819" height="591" alt="Screenshot 2026-03-18 174545" src="https://github.com/user-attachments/assets/85d2f6b1-2045-4cd9-9e3f-cf8d838a9fff" />
<img width="807" height="565" alt="Screenshot 2026-03-18 174800" src="https://github.com/user-attachments/assets/cae3c11a-93c6-4d46-b6b5-57b8fce1966a" />

</details>





<details>
  <summary>For Future</summary>
  
## here you can see what i plan to add in the future:  

**UPS HAT/stable power**   
Because it can have 2 batteries in it so it would be posible to use the device without having to be plugged into a charger.  

**Speaker**  
To hear playback with audio  

**Bigger Micro SD Card**  
32GB is enough but if i wanted to store more fotage on it, it would be nice to have more storage.  

  
</details>

<details>
  <summary>Credits</summary>
Egor Chugay,  https://grabcad.com/library/button-6x6-hole-mount-collection-1/details  

Kaan Beyaz,   https://grabcad.com/library/raspberry-pi-camera-module-v3-1  

Aleksey,      https://grabcad.com/library/2-8-inch-tft-lcd-module-1  

Spike-23,     https://grabcad.com/library/raspberry-pi-zero-2-w-with-40-pin-male-connector-1  

HackClub, amazing programs  

Stasis, amazing people and what this project is for  
</details>

<details>
  <summary>License</summary>
  
### MIT License

**Copyright (c) [2026] [TomasD-git]**

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


  
</details>
