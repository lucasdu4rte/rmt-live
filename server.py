import argparse
import asyncio
import ipaddress
import json
import random
import socket

import mss
import pyautogui
from aiohttp import WSMsgType, web
from PIL import Image

pyautogui.FAILSAFE = False

KEY_MAP = {
    "Enter": "enter", "Backspace": "backspace", "Tab": "tab", "Escape": "esc",
    "Delete": "delete", "ArrowUp": "up", "ArrowDown": "down", "ArrowLeft": "left",
    "ArrowRight": "right", "Home": "home", "End": "end", "PageUp": "pageup",
    "PageDown": "pagedown", " ": "space",
}


def local_networks():
    nets = []
    for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
        ip = info[4][0]
        nets.append(ipaddress.ip_network(f"{ip}/24", strict=False))
    return nets


def same_network(client_ip, nets):
    addr = ipaddress.ip_address(client_ip)
    if addr.is_loopback:
        return True
    return any(addr in net for net in nets)


async def index(request):
    return web.Response(text=PAGE, content_type="text/html")


async def websocket(request):
    app = request.app
    if request.query.get("pin") != app["pin"]:
        return web.Response(status=403, text="pin invalido")
    if not same_network(request.remote, app["nets"]):
        return web.Response(status=403, text="fora da rede local")

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    sender = asyncio.create_task(stream_frames(ws))
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                handle_input(json.loads(msg.data))
    finally:
        sender.cancel()
    return ws


async def stream_frames(ws):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            buf = img_to_jpeg(img)
            await ws.send_bytes(bytes([monitor["width"] >> 8, monitor["width"] & 255,
                                       monitor["height"] >> 8, monitor["height"] & 255]) + buf)
            await asyncio.sleep(1 / 12)


def img_to_jpeg(img):
    from io import BytesIO
    out = BytesIO()
    img.save(out, format="JPEG", quality=55)
    return out.getvalue()


def handle_input(ev):
    w, h = pyautogui.size()
    kind = ev.get("t")
    if kind == "move":
        pyautogui.moveTo(ev["x"] * w, ev["y"] * h, _pause=False)
    elif kind == "down":
        pyautogui.mouseDown(ev["x"] * w, ev["y"] * h, button=ev.get("b", "left"), _pause=False)
    elif kind == "up":
        pyautogui.mouseUp(ev["x"] * w, ev["y"] * h, button=ev.get("b", "left"), _pause=False)
    elif kind == "scroll":
        pyautogui.scroll(int(ev["dy"]), _pause=False)
    elif kind == "key":
        press_key(ev["key"])


def press_key(key):
    mapped = KEY_MAP.get(key)
    if mapped:
        pyautogui.press(mapped, _pause=False)
    elif len(key) == 1:
        pyautogui.typewrite(key, _pause=False)


def self_test():
    nets = [ipaddress.ip_network("192.168.1.0/24")]
    assert same_network("192.168.1.42", nets)
    assert same_network("127.0.0.1", nets)
    assert not same_network("10.0.0.5", nets)
    assert not same_network("8.8.8.8", nets)
    print("self-test ok")


def main():
    parser = argparse.ArgumentParser(description="Controle remoto da tela do Windows pela rede local")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--pin", default=None, help="PIN de acesso (padrao: gerado)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        self_test()
        return

    pin = args.pin or f"{random.randint(0, 999999):06d}"
    app = web.Application()
    app["pin"] = pin
    app["nets"] = local_networks()
    app.add_routes([web.get("/", index), web.get("/ws", websocket)])

    lan_ip = socket.gethostbyname(socket.gethostname())
    print("=" * 48)
    print(" Controle remoto rodando")
    print(f"   No mac, abra:  http://{lan_ip}:{args.port}")
    print(f"   PIN de acesso: {pin}")
    print("   (Ctrl+C para parar)")
    print("=" * 48)
    web.run_app(app, host="0.0.0.0", port=args.port, print=None)


PAGE = r"""<!doctype html><html><head><meta charset=utf-8>
<title>Controle Remoto</title>
<style>
  html,body{margin:0;background:#111;height:100%;font-family:system-ui}
  #login{color:#eee;display:flex;flex-direction:column;gap:12px;align-items:center;justify-content:center;height:100%}
  input{font-size:20px;padding:8px;border-radius:8px;border:1px solid #555;background:#222;color:#fff;text-align:center}
  button{font-size:18px;padding:10px 20px;border-radius:8px;border:0;background:#2563eb;color:#fff;cursor:pointer}
  #screen{display:none;width:100vw;height:100vh;object-fit:contain;cursor:crosshair}
</style></head><body>
<div id=login>
  <h2>Controle Remoto do Windows</h2>
  <input id=pin placeholder="PIN" inputmode=numeric>
  <button onclick=connect()>Conectar</button>
  <div id=err style=color:#f87></div>
</div>
<canvas id=screen tabindex=0></canvas>
<script>
let cv=document.getElementById('screen'),ctx=cv.getContext('2d'),ws,rw=1,rh=1;
function connect(){
  let pin=document.getElementById('pin').value.trim();
  ws=new WebSocket(`ws://${location.host}/ws?pin=${pin}`);
  ws.binaryType='arraybuffer';
  ws.onopen=()=>{document.getElementById('login').style.display='none';cv.style.display='block';cv.focus();};
  ws.onclose=()=>{document.getElementById('err').textContent='Conexao recusada (PIN ou rede).';};
  ws.onmessage=ev=>{
    let d=new Uint8Array(ev.data);
    rw=(d[0]<<8)|d[1];rh=(d[2]<<8)|d[3];
    let blob=new Blob([d.slice(4)],{type:'image/jpeg'}),url=URL.createObjectURL(blob),im=new Image();
    im.onload=()=>{cv.width=rw;cv.height=rh;ctx.drawImage(im,0,0);URL.revokeObjectURL(url);};
    im.src=url;
  };
}
function pos(e){let r=cv.getBoundingClientRect();
  let scale=Math.min(r.width/rw,r.height/rh),ox=(r.width-rw*scale)/2,oy=(r.height-rh*scale)/2;
  return {x:Math.min(1,Math.max(0,(e.clientX-r.left-ox)/(rw*scale))),
          y:Math.min(1,Math.max(0,(e.clientY-r.top-oy)/(rh*scale)))};}
let btn=['left','middle','right'];
function send(o){if(ws&&ws.readyState==1)ws.send(JSON.stringify(o));}
cv.onmousemove=e=>{let p=pos(e);send({t:'move',x:p.x,y:p.y});};
cv.onmousedown=e=>{e.preventDefault();let p=pos(e);send({t:'down',x:p.x,y:p.y,b:btn[e.button]});};
cv.onmouseup=e=>{e.preventDefault();let p=pos(e);send({t:'up',x:p.x,y:p.y,b:btn[e.button]});};
cv.oncontextmenu=e=>e.preventDefault();
cv.onwheel=e=>{e.preventDefault();send({t:'scroll',dy:e.deltaY<0?1:-1});};
cv.onkeydown=e=>{e.preventDefault();send({t:'key',key:e.key});};
</script></body></html>"""


if __name__ == "__main__":
    main()
