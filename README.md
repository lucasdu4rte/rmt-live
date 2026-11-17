# rmt-live

Controle a tela do Windows a partir do mac, pela rede local, sem senha de admin.

- **Windows**: roda um `server.py` (ou um `.exe` único) que transmite a tela e injeta mouse/teclado.
- **mac**: não instala nada — abre o navegador no IP do Windows.
- Só aceita conexões da **mesma rede** (mesma sub-rede /24) **e** com o **PIN** mostrado no console.

## No Windows (caminho fácil — sem instalar nada)

1. Entre na página **[Releases](../../releases/latest)** do repositório.
2. Baixe o `rmt-live.exe` (em *Assets*).
3. Dê dois cliques. Vai abrir uma janela preta mostrando o endereço e o PIN:

   ```
      No mac, abra:  http://192.168.0.23:8787
      PIN de acesso: 043918
   ```

   > Na primeira vez o Windows Defender pode mostrar "Windows protegeu o computador" (por ser um `.exe` sem assinatura). Clique em **Mais informações → Executar assim mesmo**. Não precisa de admin.
   >
   > Se aparecer o alerta do Firewall do Windows, marque **Redes privadas** e confirme.

4. No mac, abra esse endereço no navegador, digite o PIN e pronto — controla a tela.

Esse `.exe` é gerado automaticamente pelo GitHub Actions a cada tag `v*`. Nada de Python no Windows.

## No Windows (modo dev / CLI)

Só se quiser rodar pelo código em vez do `.exe`. Precisa de Python 3.9+ (Microsoft Store instala sem admin).

```bash
pip install --user -r requirements.txt
python server.py
```

Opções: `python server.py --port 9000 --pin 1234`.

## Gerar o `.exe` localmente (opcional)

Na própria máquina Windows com Python:

```bash
pip install --user pyinstaller
pyinstaller --onefile --name rmt-live server.py
```

Sai um único `dist/rmt-live.exe`. Para controlar janelas abertas *como administrador*, o exe teria que ser rodado elevado; para o uso normal do desktop não precisa.

## Limites conhecidos

- Transmite só o **monitor primário**, ~12 fps em JPEG (bom pra controlar, não pra vídeo).
- Tráfego **não é criptografado** (`ws://`) — ok em rede doméstica confiável; não exponha a porta pra internet.
- Teclas combinadas (Ctrl+C etc.) ainda não são enviadas; só teclas simples e de navegação.
