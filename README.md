# ReprodT – Terminal Media Player

ReprodT reproduz vídeos (MP4) e exibe imagens (PNG/JPG/WebP) diretamente no terminal, usando caracteres de bloco (▄) e cores ANSI true-color/256. Funciona em Windows, Linux e macOS sem interface gráfica.

## Funcionalidades

- Reprodução de vídeo com áudio (via FFmpeg + simpleaudio)
- Exibição de imagens estáticas
- Menu interativo (TUI) – sem argumentos de linha de comando
- Upload efêmero (copia, reproduz e apaga)
- Navegação por arquivos já enviados (`uploads/video`, `uploads/img`)
- Controle em tempo real: pause, velocidade 0.5×-2×, quit (espaço, ↑/↓, Q)
- Ajustes de colunas, altura máxima, FPS e áudio persistidos em `settings.json`
- Detecção automática de FFmpeg/FFprobe (inclui bins para Windows/Linux/Mac)

## Instalação rápida (Windows)

1. Clone ou baixe a pasta do projeto.
2. **Python 3.9+** e pip já instalados.
3. Instale dependências:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. (Opcional) Adicione `ffmpeg.exe` e `ffprobe.exe` em `ffmpeg-win\bin` ou use os bins já inclusos.
5. Execute:
   ```powershell
   python reprodT.py
   ```

## Instalação (Linux / macOS)

```bash
python3 -m pip install -r requirements.txt
python3 reprodT.py
```

Caso não tenha FFmpeg no PATH, coloque os bins em `ffmpeg-linux/` ou `ffmpeg-mac/` (veja pastas prontas no projeto).

## Como usar

- **1** – Selecionar caminho e fazer upload (vídeo ou imagem)
- **2** – Reproduzir vídeo de `uploads/video`
- **3** – Exibir imagem de `uploads/img`
- **4** – Configurações (colunas, altura máxima, FPS, áudio)
- **5** – Sobre / técnica de renderização
- **6** – Sair

Durante vídeo:
- **Espaço** – pause/resume
- **↑ / ↓** – velocidade +0.1 / −0.1 (limites 0.5×-2×)
- **Q** – sair

## Estrutura de pastas

```
reprodT/
├── requirements.txt            # dependências Python
├── source/
|   ├── reprodT.py              # código principal
|   ├── settings.json           # preferências do usuário (gerado)
|   ├── uploads/
│       ├── video/              # MP4s enviados ou selecionados
│       └── img/                # PNG/JPG/WebP
|   └── ffmpeg-{win,linux,mac}/ # bins ffmpeg
```

## Requisitos

- Python 3.9+ com pip
- FFmpeg (binários inclusos ou via PATH)
- Bibliotecas Python listadas em `requirements.txt`

## Solução de problemas

**"ffmpeg não encontrado"** – certifique-se de que `ffmpeg.exe` e `ffprobe.exe` estejam em:
- `ffmpeg-win\bin` (Windows)
- `ffmpeg-linux/` ou `ffmpeg-mac/` (Unix)
- ou adicione ao PATH do sistema.

**Sem áudio** – instale `simpleaudio` corretamente; no Windows pode exigir compilador ou usar wheel pré-compilada.

**Imagem ou vídeo não cabe no terminal** – ajuste "Colunas" e "Altura máxima" no menu Configurações.

## Contribuindo

Sinta-se à vontade para abrir issues ou pull requests. Mantenha o código compatível com Windows, Linux e macOS.

## Licença

Este projeto usa apenas bibliotecas de código aberto (Pillow, numpy, simpleaudio). FFmpeg possui sua própria licença GPL/LGPL.
