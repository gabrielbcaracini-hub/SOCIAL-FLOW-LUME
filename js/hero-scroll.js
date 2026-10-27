(function () {
  const palco = document.querySelector(".hero-foto");
  const video = palco ? palco.querySelector("video.hero-carro") : null;
  if (!palco || !video) return;

  video.muted = true;
  video.loop = false;
  video.autoplay = false;
  video.playsInline = true;
  video.pause();
  video.currentTime = 0;

  let reproduzindo = false;
  let podeIniciar = true;

  function primeiroQuadro() {
    video.pause();
    try {
      video.currentTime = 0;
    } catch (erro) {
      return;
    }
  }

  function iniciar() {
    if (reproduzindo || !podeIniciar) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    reproduzindo = true;
    podeIniciar = false;
    try {
      video.currentTime = 0;
    } catch (erro) {
      reproduzindo = false;
      podeIniciar = true;
      return;
    }
    const pedido = video.play();
    if (pedido && pedido.catch) pedido.catch(function () {
      reproduzindo = false;
      podeIniciar = true;
      primeiroQuadro();
    });
  }

  palco.addEventListener("mouseenter", iniciar);
  palco.addEventListener("mouseleave", function () {
    if (!reproduzindo) podeIniciar = true;
  });
  video.addEventListener("ended", function () {
    reproduzindo = false;
    primeiroQuadro();
  });
  video.addEventListener("loadedmetadata", primeiroQuadro);
})();
