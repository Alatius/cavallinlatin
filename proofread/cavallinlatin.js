(function() {
  var panel = document.getElementById('image-panel');
  var img = document.getElementById('image-panel-img');
  var container = document.getElementById('image-panel-img-container');
  var label = document.getElementById('image-panel-label');
  var header = document.getElementById('image-panel-header');
  var handle = document.getElementById('resize-handle');
  var currentImage = null;

  var marker = document.createElement('div');
  marker.id = 'image-panel-marker';
  container.appendChild(marker);

  var BASE_WIDTH = 410;
  var BASE_MARKER_HEIGHT = 18;
  var lastMarkerY = 0;

  function updateMarker() {
    var scale = panel.offsetWidth / BASE_WIDTH;
    var h = BASE_MARKER_HEIGHT * scale;
    marker.style.height = h + 'px';
    if (marker.style.display !== 'none') {
      var targetPx = (lastMarkerY / 100) * img.offsetHeight;
      marker.style.top = targetPx + 'px';
    }
  }

  // Create navigation buttons
  var prevBtn = document.createElement('button');
  prevBtn.id = 'image-panel-prev';
  prevBtn.textContent = '◀';
  header.insertBefore(prevBtn, label);

  var nextBtn = document.createElement('button');
  nextBtn.id = 'image-panel-next';
  nextBtn.textContent = '▶';
  header.appendChild(nextBtn);

  // Resize handle drag logic
  var dragging = false;

  handle.addEventListener('mousedown', function(e) {
    e.preventDefault();
    dragging = true;
    handle.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    var newWidth = document.documentElement.clientWidth - e.clientX - handle.offsetWidth;
    if (newWidth < 150) newWidth = 150;
    if (newWidth > document.documentElement.clientWidth - 200) {
      newWidth = document.documentElement.clientWidth - 200;
    }
    panel.style.width = newWidth + 'px';
    updateMarker();
  });

  document.addEventListener('mouseup', function() {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    localStorage.setItem('image-panel-width', parseInt(panel.style.width));
  });

  function parseImageName(name) {
    var match = name.match(/^cavlat-(\d+)-(\d+)\.png$/);
    if (!match) return null;
    return { vol: parseInt(match[1]), num: parseInt(match[2]) };
  }

  function getNextImage(imageName) {
    var parsed = parseImageName(imageName);
    if (!parsed) return null;

    if (parsed.vol === 1 && parsed.num === 1160) {
      return 'cavlat-2-0001.png';
    }
    var nextNum = parsed.num + 1;
    return 'cavlat-' + parsed.vol + '-' + String(nextNum).padStart(4, '0') + '.png';
  }

  function getPrevImage(imageName) {
    var parsed = parseImageName(imageName);
    if (!parsed) return null;

    if (parsed.vol === 2 && parsed.num === 1) {
      return 'cavlat-1-1160.png';
    }
    var prevNum = parsed.num - 1;
    if (prevNum < 1) return null;
    return 'cavlat-' + parsed.vol + '-' + String(prevNum).padStart(4, '0') + '.png';
  }

  function showImage(imageName, y, showMarker) {
    if (!imageName) return;
    y = y || 0;
    currentImage = imageName;
    var png = 'columns/' + imageName;

    label.textContent = imageName;
    marker.style.display = showMarker ? 'block' : 'none';
    lastMarkerY = y;

    function scrollToY() {
      if (showMarker) {
        updateMarker();
        var targetPx = (y / 100) * img.offsetHeight;
        container.scrollTop = targetPx - container.clientHeight / 4;
      } else {
        container.scrollTop = y === 100 ? img.offsetHeight : 0;
      }
    }

    if (img.getAttribute('src') === png) {
      scrollToY();
    } else {
      img.onload = function() {
        scrollToY();
        img.onload = null;
      };
      img.src = png;
    }
  }

  prevBtn.addEventListener('click', function() {
    if (currentImage) {
      var prev = getPrevImage(currentImage);
      if (prev) showImage(prev, 100, false);
    }
  });

  nextBtn.addEventListener('click', function() {
    if (currentImage) {
      var next = getNextImage(currentImage);
      if (next) showImage(next, 0, false);
    }
  });

  document.body.addEventListener('click', function(e) {
    var orth = e.target.closest('orth[data-img]');
    if (!orth) return;

    var img_base = orth.getAttribute('data-img');
    var y = parseFloat(orth.getAttribute('data-y')) || 0;
    showImage(img_base, y, true);
  });

  // Show first image on load
  showImage('cavlat-1-0001.png', 0, false);
})();
