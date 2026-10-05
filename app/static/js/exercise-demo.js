// ------------------------------------------------------------------
// FitFuel — exercise demo popup (video link + photos + step-by-step)
// ------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    var dataEl = document.getElementById('exercise-guide-data');
    var modalEl = document.getElementById('exerciseModal');
    if (!dataEl || !modalEl) return;

    var guide = {};
    try { guide = JSON.parse(dataEl.textContent) || {}; } catch (e) { return; }

    var imgBase = modalEl.getAttribute('data-img-base') || '/static/img/';
    var titleEl = document.getElementById('exerciseModalTitle');
    var tagsEl = document.getElementById('exerciseModalTags');
    var imagesEl = document.getElementById('exerciseModalImages');
    var stepsEl = document.getElementById('exerciseModalSteps');
    var videoEl = document.getElementById('exerciseModalVideo');

    function addTag(text) {
        if (!text) return;
        var span = document.createElement('span');
        span.className = 'exercise-tag';
        span.textContent = text;
        tagsEl.appendChild(span);
    }

    function openDemo(name) {
        var info = guide[name];
        if (!info) return;

        // textContent (not innerHTML) everywhere, so nothing in the data can inject HTML.
        titleEl.textContent = name;

        tagsEl.textContent = '';
        addTag(info.muscle ? info.muscle.charAt(0).toUpperCase() + info.muscle.slice(1) : '');
        addTag(info.equipment);
        addTag(info.level);

        imagesEl.textContent = '';
        var labels = ['Start', 'Finish'];
        (info.images || []).forEach(function (path, i) {
            var col = document.createElement('div');
            col.className = 'col-6';
            var wrap = document.createElement('figure');
            wrap.className = 'exercise-figure';
            var img = document.createElement('img');
            img.src = imgBase + path;
            img.alt = name + ' - ' + (labels[i] || 'position ' + (i + 1));
            img.loading = 'lazy';
            var cap = document.createElement('figcaption');
            cap.textContent = labels[i] || 'Position ' + (i + 1);
            wrap.appendChild(img);
            wrap.appendChild(cap);
            col.appendChild(wrap);
            imagesEl.appendChild(col);
        });

        stepsEl.textContent = '';
        (info.steps || []).forEach(function (step) {
            var li = document.createElement('li');
            li.textContent = step;
            stepsEl.appendChild(li);
        });

        if (info.youtube_link) {
            videoEl.href = info.youtube_link;
            videoEl.classList.remove('d-none');
        } else {
            videoEl.classList.add('d-none');
        }

        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }

    document.addEventListener('click', function (event) {
        var btn = event.target.closest('.btn-demo');
        if (!btn) return;
        event.preventDefault();
        openDemo(btn.getAttribute('data-exercise'));
    });
});
