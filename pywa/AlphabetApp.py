import os
import json

# Folder where everything will be created
output_dir = "alphabet-pwa"

os.makedirs(output_dir, exist_ok=True)

# 1. index.html — full-screen alphabet app for kids
index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="mobile-web-app-capable" content="yes">
  <title>ABC Fun</title>

  <!-- PWA manifest -->
  <link rel="manifest" href="manifest.json">

  <!-- Theme & icons -->
  <meta name="theme-color" content="#ff4500">

  <style>
    html, body {
      margin: 0; padding: 0;
      height: 100%; width: 100%;
      overflow: hidden;
      background: linear-gradient(to bottom, #f0f8ff, #e0f7fa);
      font-family: "Comic Sans MS", cursive, sans-serif;
      display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      touch-action: manipulation;
    }
    #letter {
      font-size: 22vh;
      color: #ff4500;
      margin: 0;
      text-shadow: 4px 4px 8px rgba(0,0,0,0.2);
      transition: transform 0.3s, color 0.4s;
    }
    #letter:active { transform: scale(1.15); color: #32cd32; }
    #word {
      font-size: 8vh;
      color: #4169e1;
      margin: 20px 0;
      text-align: center;
      padding: 0 20px;
    }
    #controls {
      position: absolute;
      bottom: 6vh;
      width: 90%;
      display: flex;
      justify-content: space-between;
    }
    button {
      font-size: 6vh;
      padding: 2vh 5vw;
      background: #ffd700;
      border: 3px solid #ff8c00;
      border-radius: 20px;
      color: #d2691e;
      font-weight: bold;
      cursor: pointer;
    }
    button:active { background: #ffcc00; transform: scale(0.95); }
    @media (orientation: landscape) {
      #letter { font-size: 18vw; }
      #word   { font-size: 6vw; }
      button  { font-size: 5vw; padding: 1.5vh 4vw; }
    }
  </style>
</head>
<body>
  <div id="letter">A</div>
  <div id="word">Apple 🍎</div>

  <div id="controls">
    <button onclick="prev()">← Previous</button>
    <button onclick="next()">Next →</button>
  </div>

  <script src="register-sw.js"></script>
  <script>
    const alphabet = [
      {letter:"A", word:"Apple 🍎"}, {letter:"B", word:"Ball ⚽"}, {letter:"C", word:"Cat 🐱"},
      {letter:"D", word:"Dog 🐶"},   {letter:"E", word:"Elephant 🐘"}, {letter:"F", word:"Fish 🐟"},
      {letter:"G", word:"Giraffe 🦒"}, {letter:"H", word:"Hat 🎩"}, {letter:"I", word:"Ice Cream 🍦"},
      {letter:"J", word:"Jelly 🍮"}, {letter:"K", word:"Kite 🪁"}, {letter:"L", word:"Lion 🦁"},
      {letter:"M", word:"Monkey 🐒"}, {letter:"N", word:"Nest 🪺"}, {letter:"O", word:"Orange 🍊"},
      {letter:"P", word:"Penguin 🐧"}, {letter:"Q", word:"Queen 👑"}, {letter:"R", word:"Rabbit 🐰"},
      {letter:"S", word:"Sun ☀️"},   {letter:"T", word:"Tiger 🐅"}, {letter:"U", word:"Umbrella ☂️"},
      {letter:"V", word:"Violin 🎻"}, {letter:"W", word:"Whale 🐳"}, {letter:"X", word:"Xylophone 🎶"},
      {letter:"Y", word:"Yak 🐃"},   {letter:"Z", word:"Zebra 🦓"}
    ];

    let idx = 0;
    const letterEl = document.getElementById("letter");
    const wordEl   = document.getElementById("word");

    function update() {
      letterEl.textContent = alphabet[idx].letter;
      wordEl.textContent   = alphabet[idx].word;
    }

    function next() { idx = (idx + 1) % alphabet.length; update(); }
    function prev() { idx = (idx - 1 + alphabet.length) % alphabet.length; update(); }

    update();

    // Try fullscreen (works best after user interaction on some browsers)
    document.addEventListener("click", () => {
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    }, {once: true});
  </script>
</body>
</html>
"""

with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(index_html)

# 2. manifest.json
manifest = {
    "name": "ABC Fun - Learn Alphabet",
    "short_name": "ABC Fun",
    "description": "Fun offline app for kids to learn A to Z with big letters and words!",
    "start_url": ".",
    "display": "fullscreen",
    "orientation": "any",
    "background_color": "#f0f8ff",
    "theme_color": "#ff4500",
    "icons": [
        {
            "src": "icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable"
        }
    ]
}

with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

# 3. sw.js — simple cache-first offline service worker
sw_js = """const CACHE_NAME = "abc-fun-v1";
const urlsToCache = [
  ".",
  "index.html",
  "manifest.json"
  // add "icon-192.png", "icon-512.png" when you have them
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
"""

with open(os.path.join(output_dir, "sw.js"), "w", encoding="utf-8") as f:
    f.write(sw_js)

# 4. register-sw.js — registers the service worker
register_js = """if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js")
      .then(reg => console.log("Service Worker registered", reg))
      .catch(err => console.log("Service Worker registration failed:", err));
  });
}
"""

with open(os.path.join(output_dir, "register-sw.js"), "w", encoding="utf-8") as f:
    f.write(register_js)

# 5. Instructions file
instructions = """
Alphabet PWA created!

To use:
1. Put icon-192.png and icon-512.png into this folder (optional but recommended)
   → You can create them at https://favicon.io or similar (use bright kid-friendly image)

2. Open index.html in browser (double-click or file://)

3. For full PWA experience:
   - Serve via http(s) (e.g. python -m http.server 8000)
   - Visit http://localhost:8000
   - "Add to home screen" / install prompt should appear

Works offline after first load — perfect for tablets & phones!
"""

with open(os.path.join(output_dir, "README-how-to-use.txt"), "w", encoding="utf-8") as f:
    f.write(instructions)

print(f"PWA files generated in folder: {output_dir}")
print("→ Open index.html or serve the folder with:")
print(f"   cd {output_dir}")
print("   python -m http.server 8000")
print("Then visit http://localhost:8000 in your phone/tablet browser.")