from PIL import Image, ImageDraw, ImageFont
import base64, io, json
from pathlib import Path

def font(sz):
    for p in ["C:/Windows/Fonts/malgunbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

def make(sz):
    img = Image.new("RGBA",(sz,sz),(0,0,0,0)); d=ImageDraw.Draw(img)
    r=int(sz*0.22)
    d.rounded_rectangle([0,0,sz-1,sz-1], radius=r, fill=(20,26,38,255))
    # shield
    m=sz*0.20; w=sz-2*m; top=m*1.05; bot=sz-m*0.85
    cx=sz/2
    pts=[(cx-w/2, top),(cx+w/2, top),(cx+w/2, top+(bot-top)*0.45),(cx, bot),(cx-w/2, top+(bot-top)*0.45)]
    d.polygon(pts, fill=(42,120,214,255))
    # check
    lw=max(2,int(sz*0.055))
    d.line([(cx-w*0.22, top+(bot-top)*0.42),(cx-w*0.03, top+(bot-top)*0.60),(cx+w*0.26, top+(bot-top)*0.22)],
           fill=(255,255,255,255), width=lw, joint="curve")
    return img

def encoded_icons():
    out = {}
    for size in (192, 512):
        buf = io.BytesIO()
        make(size).save(buf, "PNG", optimize=True)
        out[size] = base64.b64encode(buf.getvalue()).decode("ascii")
    return out


if __name__ == "__main__":
    out = encoded_icons()
    target = Path("icons.json")
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for size, payload in out.items():
        print(size, "b64len", len(payload))
    print(f"wrote {target.resolve()}")
