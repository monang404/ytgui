let eqCtx;
const NUM_BANDS = 12;
const bandHeights = new Array(NUM_BANDS).fill(0);
const bandTargets = new Array(NUM_BANDS).fill(0);
const eqGradients = [];

function initEQ() {
    if(!dom.eqCanvas) return;
    eqCtx = dom.eqCanvas.getContext("2d");
    const canvasH = dom.eqCanvas.height;
    for (let i = 0; i < NUM_BANDS; i++) {
        const grad = eqCtx.createLinearGradient(0, canvasH, 0, 0);
        const hue = 340 + (i / NUM_BANDS) * 60;
        grad.addColorStop(0, `hsla(${hue}, 80%, 55%, 0.9)`);
        grad.addColorStop(0.5, `hsla(${hue + 20}, 70%, 50%, 0.7)`);
        grad.addColorStop(1, `hsla(${hue + 40}, 60%, 65%, 0.5)`);
        eqGradients.push(grad);
    }
    requestAnimationFrame(tickEQ);
}

function tickEQ() {
    if (!eqCtx) return;
    if (store.active_tab !== "home") {
        requestAnimationFrame(tickEQ);
        return;
    }

    const canvas = dom.eqCanvas;
    const w = canvas.width;
    const h = canvas.height;
    const isPlaying = store.status === "PLAYING";

    eqCtx.clearRect(0, 0, w, h);

    const gap = 4;
    const bandW = (w - gap * (NUM_BANDS - 1)) / NUM_BANDS;

    for (let i = 0; i < NUM_BANDS; i++) {
        if (isPlaying) {
            bandTargets[i] = Math.random() * h * 0.85 + h * 0.1;
        } else {
            bandTargets[i] = h * 0.05;
        }

        bandHeights[i] += (bandTargets[i] - bandHeights[i]) * 0.18;

        const bh = bandHeights[i];
        const x = i * (bandW + gap);
        const y = h - bh;

        eqCtx.fillStyle = eqGradients[i];
        eqCtx.beginPath();
        const r = Math.min(bandW / 2, 4);
        eqCtx.moveTo(x, h);
        eqCtx.lineTo(x, y + r);
        eqCtx.quadraticCurveTo(x, y, x + r, y);
        eqCtx.lineTo(x + bandW - r, y);
        eqCtx.quadraticCurveTo(x + bandW, y, x + bandW, y + r);
        eqCtx.lineTo(x + bandW, h);
        eqCtx.closePath();
        eqCtx.fill();
    }

    requestAnimationFrame(tickEQ);
}
