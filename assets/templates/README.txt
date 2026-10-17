# Antigravity Auto Allow — template folder

Image fallback သုံးချင်ရင် ဒီ folder ထဲမှာ Allow/Submit button ရဲ့ **ပုံဖြတ် (crop)** တွေ
PNG အနေနဲ့ ထည့်ပါ။ ဖိုင်နာမည်ရဲ့ အရှေ့ပိုင်း (stem) ကို label အနေနဲ့ ယူတယ်။

ဥပမာ
    allow.png     -> label "allow"
    submit.png    -> label "submit"
    run.png       -> label "run"

ရိုက်နည်း
    1. python agy_auto_allow.py --grab
       (Antigravity window ကို screenshot ရိုက်ပြီး assets\screenshots\ ထဲ သိမ်းတယ်)
    2. Paint နဲ့ ဖွင့် → Allow button ကို အနီး ပတ်လည် အနည်းငယ် ချန်ပြီး crop → PNG အနေနဲ့ သိမ်း
    3. ဒီ folder ထဲ ထည့်
    4. config.json မှာ  "image_fallback": { "enabled": true, "threshold": 0.88 }

သတိထားရန်: ဒီ mode က window က ဖန်သားပြင်ပေါ် မြင်နေရမယ် (occluded/minimize ဖြစ်ရင် မလုပ်ဘူး)။
UIA (ပုံမှန် mode) က အဲဒီထက် ပိုကောင်းပြီး background မှာ အလုပ်လုပ်တယ်။
