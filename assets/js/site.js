/* Tệp sinh tự động từ src/js bởi tools/build.py. Sửa ở src/js. */
/* Nhật ký xây nhà · JavaScript dùng chung cho mọi trang.
   Mỗi tính năng tự kiểm tra phần tử của nó có trên trang không, nên trang nào cũng nạp được tệp này.
   Không gửi dữ liệu đi đâu: mọi thứ chỉ lưu trong trình duyệt của người đọc (localStorage). */
(function(){
  'use strict';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function(id){ return document.getElementById(id); };
  function store(key, val) {
    try {
      if (val === undefined) return JSON.parse(localStorage.getItem(key) || 'null');
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) { return null; }
  }
  function copyText(text, status, wrap, area, ok) {
    function fallback() {
      if (wrap) wrap.hidden = false;
      if (area) { area.value = text; area.focus(); area.select(); }
      if (status) status.textContent = 'Trình duyệt chưa cho sao chép tự động. Đoạn bên dưới đã được bôi đen, hãy nhấn Ctrl+C hoặc giữ để sao chép.';
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function(){ if (status) status.textContent = ok; }).catch(fallback);
    else fallback();
  }
  function todayISO() { var d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }
  function fold(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase(); }

  /* ---------- Nhớ trang đã đọc, trang gần nhất ---------- */
  var path = location.pathname.replace(/index\.html$/, '');
  var page = document.body.dataset;
  if (page.kind && page.kind !== 'home' && page.kind !== 'search' && page.kind !== '404') {
    var seen = store('nkxn-da-doc') || [];
    if (seen.indexOf(path) < 0) { seen.push(path); if (seen.length > 400) seen = seen.slice(-400); store('nkxn-da-doc', seen); }
    if (page.title) store('nkxn-gan-nhat', { u: path, t: page.title, k: page.kindLabel || '' });
  }

  /* ---------- Thước độ sâu: tô các tầng đã đọc ---------- */
  var seenList = store('nkxn-da-doc') || [];
  document.querySelectorAll('.ruler li[data-urls]').forEach(function(li){
    var urls = li.dataset.urls ? li.dataset.urls.split('|') : [];
    if (urls.some(function(u){ return seenList.indexOf(u) > -1; })) li.classList.add('is-seen');
  });

  /* ---------- Trang chủ: "Nhà bạn đang ở đâu?" và "Đọc tiếp" ---------- */
  document.querySelectorAll('.where-opt').forEach(function(a){
    a.addEventListener('click', function(){ store('nkxn-o-dau', { label: a.dataset.label, href: a.getAttribute('href') }); });
  });
  var welcome = $('welcome');
  if (welcome) {
    var mine = store('nkxn-o-dau'), last = store('nkxn-gan-nhat');
    if (mine || last) {
      var parts = [];
      if (mine) parts.push('Nhà bạn: <a href="' + mine.href + '">' + mine.label + '</a>');
      if (last && last.u) parts.push('Đọc tiếp: <a href="' + last.u + '">' + last.t.replace(/</g, '&lt;') + '</a>');
      $('welcome-text').innerHTML = 'Chào bạn trở lại. ' + parts.join(' · ');
      welcome.hidden = false;
      document.querySelectorAll('.where-opt').forEach(function(a){ if (mine && a.dataset.label === mine.label) a.classList.add('is-mine'); });
      $('welcome-reset').addEventListener('click', function(){
        try { localStorage.removeItem('nkxn-o-dau'); localStorage.removeItem('nkxn-gan-nhat'); } catch (e) {}
        welcome.hidden = true;
        document.querySelectorAll('.where-opt').forEach(function(a){ a.classList.remove('is-mine'); });
      });
    }
  }

  /* ---------- Tranh trang chủ: tám trạm trên con đường ---------- */
  var road = $('road-path'), g = $('stations');
  if (road && g && road.getTotalLength) {
    var L = road.getTotalLength(), ns = 'http://www.w3.org/2000/svg';
    for (var i = 0; i < 8; i++) {
      var p = road.getPointAtLength(L * (0.07 + i * 0.113));
      var c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', p.x); c.setAttribute('cy', p.y); c.setAttribute('r', 14);
      c.setAttribute('fill', i === 0 ? '#E6B53C' : '#FBFBF6'); c.setAttribute('stroke', '#1E2A4C'); c.setAttribute('stroke-width', '2.5');
      var t = document.createElementNS(ns, 'text');
      t.setAttribute('x', p.x); t.setAttribute('y', p.y + 6); t.setAttribute('text-anchor', 'middle');
      t.setAttribute('font-size', '17'); t.setAttribute('fill', '#1E2A4C'); t.setAttribute('class', 'svg-hand');
      t.textContent = String(i + 1);
      g.appendChild(c); g.appendChild(t);
    }
  }
  if (reduce) document.querySelectorAll('svg').forEach(function(s){ if (s.pauseAnimations) s.pauseAnimations(); });

  /* ---------- Truyện: tranh cuộn và thanh tiến độ ---------- */
  function setScene(story, n) {
    var stage = story && story.querySelector('.stage');
    if (!stage) return;
    n = String(n);
    if (stage.dataset.scene !== n) stage.dataset.scene = n;
    var cur = story.querySelector('.step[data-step="' + n + '"] .step-n');
    var cap = stage.querySelector('.cap-t'); if (cap) cap.textContent = cur ? cur.textContent : '';
    stage.querySelectorAll('.dots i').forEach(function(d, i){ d.classList.toggle('on', i < Number(n)); });
    story.querySelectorAll('.step').forEach(function(s){ s.classList.toggle('is-active', s.dataset.step === n); });
  }
  var story = document.querySelector('article.story');
  if (story) {
    setScene(story, 1);
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(en){ if (en.isIntersecting) setScene(story, en.target.dataset.step); });
      }, { rootMargin: window.innerWidth <= 860 ? '-58% 0px -32% 0px' : '-48% 0px -42% 0px' });
      story.querySelectorAll('.step').forEach(function(s){ io.observe(s); });
    }
    var progress = $('progress'), bar = progress && progress.querySelector('span');
    if (bar) {
      progress.hidden = false;
      var upd = function(){
        var r = story.getBoundingClientRect();
        var total = Math.max(1, story.offsetHeight - window.innerHeight);
        bar.style.transform = 'scaleX(' + Math.min(1, Math.max(0, -r.top / total)) + ')';
      };
      window.addEventListener('scroll', upd, { passive: true });
      window.addEventListener('resize', upd);
      upd();
    }
  }

  /* ---------- Truyện: đọc bằng bàn phím ----------
     ↓, Page Down, phím cách: sang cảnh tiếp. ↑, Page Up, Shift + phím cách: về cảnh trước.
     Không bắt phím khi đang gõ trong ô nhập, khi giữ Ctrl/Alt/Cmd, hoặc khi đã đọc qua cảnh cuối. */
  if (story && story.querySelector('.step')) {
    var steps = Array.prototype.slice.call(story.querySelectorAll('.step'));
    var storyEnd = story.querySelector('.story-end');
    var pending = null, pendingTimer;
    var lineY = function(){ return window.innerHeight * (window.innerWidth <= 860 ? 0.56 : 0.42); };
    var goTo = function(el, ratio){
      var y = window.scrollY + el.getBoundingClientRect().top - (ratio === undefined ? lineY() : window.innerHeight * ratio);
      window.scrollTo({ top: Math.max(0, y), behavior: reduce ? 'auto' : 'smooth' });
    };
    var currentIndex = function(){
      if (pending !== null) return pending;
      var first = steps[0].getBoundingClientRect();
      if (first.top > lineY() + 4) return -1;              /* còn ở đầu trang, chưa vào cảnh 1 */
      var act = steps.findIndex(function(s){ return s.classList.contains('is-active'); });
      return act < 0 ? 0 : act;
    };
    document.addEventListener('keydown', function(e){
      if (e.defaultPrevented || e.ctrlKey || e.altKey || e.metaKey) return;
      var t = e.target, tag = t && t.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'BUTTON' || tag === 'A' || (t && t.isContentEditable)) return;
      var k = e.key, dir = 0;
      if (k === 'ArrowDown' || k === 'PageDown' || (k === ' ' && !e.shiftKey)) dir = 1;
      else if (k === 'ArrowUp' || k === 'PageUp' || (k === ' ' && e.shiftKey)) dir = -1;
      if (!dir) return;
      var endTop = storyEnd ? storyEnd.getBoundingClientRect().top : Infinity;
      if (dir > 0 && endTop < window.innerHeight * 0.9) return;   /* đã tới phần cuối truyện: cuộn bình thường */
      if (dir < 0 && endTop < window.innerHeight * 0.5) {          /* đang ở phần cuối: quay lại cảnh cuối */
        e.preventDefault(); pending = steps.length - 1; goTo(steps[pending]);
      } else {
        var i = currentIndex() + dir;
        if (dir < 0 && currentIndex() === -1) return;              /* đầu trang: để trình duyệt cuộn */
        e.preventDefault();
        if (i < 0) { pending = -1; window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' }); }
        else if (i >= steps.length) { pending = steps.length; if (storyEnd) goTo(storyEnd, 0.12); }
        else { pending = i; goTo(steps[i]); setScene(story, steps[i].dataset.step); }
      }
      clearTimeout(pendingTimer);
      pendingTimer = setTimeout(function(){ pending = null; }, reduce ? 50 : 700);
    });
  }

  /* ---------- Cổng chặng, bản đồ, sổ hành trình ----------
     nkxn-cong = { "1": [0, 2], ... }: các việc đã đánh dấu ở Cổng chặng của từng chặng. */
  var gateBoxes = document.querySelectorAll('input[data-gate]');
  var stamps = document.querySelectorAll('.stamp[data-stage]');
  var mapSecs = document.querySelectorAll('.mstage[data-stage]');
  if (gateBoxes.length || stamps.length || mapSecs.length) {
    var gates = function(){ return store('nkxn-cong') || {}; };
    var stateOf = function(n, total, urls){
      var g = gates()[n] || [];
      if (total > 0 && g.length >= total) return 'done';
      if (g.length || urls.some(function(u){ return seenList.indexOf(u) > -1; })) return 'seen';
      return '';
    };
    var setState = function(el, st){
      el.classList.toggle('is-done', st === 'done');
      el.classList.toggle('is-seen', st === 'seen');
    };
    var refresh = function(){
      var g = gates();
      var totals = {};
      gateBoxes.forEach(function(b){
        var n = b.dataset.gate;
        totals[n] = (totals[n] || 0) + 1;
        b.checked = (g[n] || []).indexOf(+b.dataset.i) > -1;
      });
      Object.keys(totals).forEach(function(n){
        var done = (g[n] || []).length, total = totals[n];
        document.querySelectorAll('.gate-count[data-stage="' + n + '"]').forEach(function(c){
          c.textContent = done + '/' + total + (c.tagName === 'SMALL' ? '' : ' việc');
        });
        document.querySelectorAll('.gate[data-stage="' + n + '"] .gate-done, .mp-gate[data-stage="' + n + '"] .gate-done').forEach(function(d){
          d.hidden = done < total;
        });
      });
      mapSecs.forEach(function(sec){
        var n = sec.dataset.stage;
        var st = stateOf(n, totals[n] || 0, (sec.dataset.urls || '').split('|'));
        var badge = sec.querySelector('.mstage-state');
        if (badge) { badge.textContent = st === 'done' ? 'Đã qua cổng' : st === 'seen' ? 'Đã đọc vài bài' : ''; setState(badge, st); }
        document.querySelectorAll('.map-stop[data-stage="' + n + '"], .mg-stop[data-stage="' + n + '"], .map-jump a[data-stage="' + n + '"]').forEach(function(el){ setState(el, st); });
      });
      if (stamps.length) {
        var passed = 0, nextStage = null;
        stamps.forEach(function(s){
          var n = s.dataset.stage;
          var st = stateOf(n, +s.dataset.total || 0, (s.dataset.urls || '').split('|'));
          setState(s, st);
          s.querySelector('.stamp-s').textContent = st === 'done' ? 'Đã qua cổng' : st === 'seen' ? 'Đang đi' : 'Chưa đi';
          if (st === 'done') passed++;
          else if (!nextStage) nextStage = s;
        });
        var text = $('passport-text');
        var read = seenList.filter(function(u){ return u.indexOf('/chuyen/') === 0; }).length;
        var anySeen = document.querySelector('.stamp.is-seen, .stamp.is-done');
        if (text && anySeen) {
          var msg = 'Bạn đã đọc ' + read + '/' + text.dataset.stories + ' câu chuyện và qua ' + passed + '/8 cổng chặng.';
          if (nextStage) {
            msg += ' Chặng nên xem tiếp: <a href="/chang/' + nextStage.dataset.stage + '/">' + nextStage.querySelector('.stamp-n').textContent + ' · ' + nextStage.querySelector('.stamp-l').textContent + '</a>.';
          } else msg += ' Bạn đã đi hết tám chặng.';
          text.innerHTML = msg;
        }
      }
    };
    gateBoxes.forEach(function(b){
      b.addEventListener('change', function(){
        var g = gates(), n = b.dataset.gate, i = +b.dataset.i;
        var list = (g[n] || []).filter(function(x){ return x !== i; });
        if (b.checked) list.push(i);
        list.sort(function(x, y){ return x - y; });
        g[n] = list;
        store('nkxn-cong', g);
        refresh();
      });
    });
    var reset = $('passport-reset');
    if (reset) {
      var armed = false;
      reset.addEventListener('click', function(){
        if (!armed) { armed = true; reset.textContent = 'Bấm lần nữa để xoá hẳn'; setTimeout(function(){ armed = false; reset.textContent = 'Xoá sổ'; }, 4000); return; }
        try { ['nkxn-cong', 'nkxn-da-doc', 'nkxn-gan-nhat', 'nkxn-o-dau'].forEach(function(k){ localStorage.removeItem(k); }); } catch (e) {}
        location.reload();
      });
    }
    refresh();
  }

  /* Bản đồ: mở hết các mục trên màn hình rộng, nút mở/thu, in, đánh dấu chặng đang xem */
  var panels = document.querySelectorAll('.mpanel');
  if (panels.length) {
    var expand = $('map-expand');
    var setAll = function(open){
      panels.forEach(function(p){ p.open = open; });
      if (expand) { expand.textContent = open ? 'Thu gọn các mục' : 'Mở hết các mục'; expand.setAttribute('aria-pressed', open ? 'true' : 'false'); }
    };
    if (window.matchMedia && matchMedia('(min-width: 861px)').matches) setAll(true);
    if (expand) expand.addEventListener('click', function(){ setAll(expand.getAttribute('aria-pressed') !== 'true'); });
    var pr = $('map-print');
    if (pr) pr.addEventListener('click', function(){ setAll(true); window.print(); });
    window.addEventListener('beforeprint', function(){ setAll(true); });
  }
  var jumps = document.querySelectorAll('.map-jump a');
  if (jumps.length && mapSecs.length && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if (!en.isIntersecting) return;
        jumps.forEach(function(a){ a.classList.toggle('is-here', a.dataset.stage === en.target.dataset.stage); });
      });
    }, { rootMargin: '-35% 0px -60% 0px' });
    mapSecs.forEach(function(s){ io.observe(s); });
  }

  /* ---------- Thẻ lật mặt sau ---------- */
  document.querySelectorAll('.flip').forEach(function(f){
    var btn = f.querySelector('.flip-btn'), back = f.querySelector('.flip-back');
    if (!btn || !back) return;
    btn.addEventListener('click', function(){
      var open = back.hidden;
      back.hidden = !open;
      btn.setAttribute('aria-expanded', String(open));
      btn.textContent = open ? 'Gập lại' : 'Lật mặt sau';
      if (open && !reduce) { back.classList.remove('turn-in'); void back.offsetWidth; back.classList.add('turn-in'); }
    });
  });

  /* ---------- Công cụ: danh sách tick ---------- */
  function renderTally(n) {
    var box = $('tally'), txt = $('tally-text');
    if (!box || !txt) return;
    var html = '';
    for (var g = 0; g < Math.ceil(n / 5); g++) {
      var k = Math.min(5, n - g * 5), s = '<svg viewBox="0 0 44 36">';
      for (var i = 0; i < Math.min(k, 4); i++) s += '<line x1="' + (6 + i * 10) + '" y1="4" x2="' + (6 + i * 10) + '" y2="32" stroke="#C4553B" stroke-width="3.5" stroke-linecap="round"/>';
      if (k === 5) s += '<line x1="2" y1="28" x2="42" y2="8" stroke="#C4553B" stroke-width="3.5" stroke-linecap="round"/>';
      html += s + '</svg>';
    }
    box.innerHTML = html;
    txt.textContent = n === 0 ? 'Chưa có chỗ nào phải lắc đầu. Đi thêm một vòng nữa cho chắc.' : 'Bà lắc đầu ở ' + n + ' chỗ. Sửa xong hết rồi hãy nhận chìa khóa.';
  }
  document.querySelectorAll('ul.checks').forEach(function(ul){
    var key = 'shanco-' + ul.dataset.key;
    var boxes = Array.prototype.slice.call(ul.querySelectorAll('input[type=checkbox]'));
    var saved = store(key) || [];
    boxes.forEach(function(b){ if (saved.indexOf(b.id) > -1) b.checked = true; });
    var prog = document.querySelector('.ck-progress[data-for="' + ul.dataset.key + '"]');
    function upd() {
      var on = boxes.filter(function(b){ return b.checked; });
      if (prog) prog.textContent = on.length === boxes.length ? 'Xong cả ' + boxes.length + ' việc.' : on.length + '/' + boxes.length + ' việc đã xong';
      store(key, on.map(function(b){ return b.id; }));
      if (ul.dataset.key === 'ck-nck') renderTally(on.length);
    }
    boxes.forEach(function(b){ b.addEventListener('change', upd); });
    upd();
  });

  /* ---------- Công cụ: có cần xin phép không ---------- */
  var quiz = $('gp-quiz');
  if (quiz) {
    var res = $('gp-result');
    quiz.addEventListener('submit', function(e){ e.preventDefault(); });
    quiz.addEventListener('change', function(){
      function v(n){ var c = quiz.querySelector('input[name="' + n + '"]:checked'); return c ? c.value : null; }
      var q1 = v('gp-q1'), q2 = v('gp-q2'), q3 = v('gp-q3');
      var cls = '', main = '';
      if (q1 === 'co') { cls = 'is-must'; main = 'Gần như chắc chắn phải xin giấy phép. Nhà từ 7 tầng hoặc từ 500 m² sàn không thuộc diện miễn của nhà ở riêng lẻ.'; }
      else if (q2 === 'co') { cls = 'is-must'; main = 'Nhiều khả năng phải xin giấy phép. Khu đô thị, khu dân cư hoặc khu có quản lý kiến trúc không được miễn, dù nhà dưới 7 tầng.'; }
      else if (q2 === 'chua') { cls = 'is-ask'; main = 'Hãy hỏi UBND xã hoặc phường trước. Chỉ cần biết lô đất nằm trong khu nào là trả lời được câu này.'; }
      else if (q1 === 'khong' && q2 === 'khong') { cls = 'is-maybe'; main = 'Có thể thuộc diện miễn giấy phép. Hãy xin văn bản xác nhận của xã hoặc phường và cất vào hộp hồ sơ.'; }
      else { res.className = 'result'; res.textContent = 'Trả lời câu 1 và câu 2 để xem gợi ý.'; return; }
      var extra = '';
      if (q3 === 'co') extra = 'Đất trong khu đã có quy hoạch nhưng chưa thực hiện có thể chỉ được cấp giấy phép có thời hạn, kèm cam kết tự phá dỡ khi Nhà nước thu hồi đất.';
      else if (q3 === 'chua') extra = 'Khi lên phường, hỏi thêm lô đất có nằm trong quy hoạch chưa thực hiện không.';
      res.className = 'result ' + cls;
      res.innerHTML = '';
      var p1 = document.createElement('strong'); p1.textContent = main; res.appendChild(p1);
      if (extra) { var p2 = document.createElement('p'); p2.textContent = extra; res.appendChild(p2); }
    });
  }

  /* ---------- Công cụ: so ba báo giá ---------- */
  var body = $('cmp-body');
  if (body) {
    var rows = ['Cách tính diện tích móng', 'Cách tính diện tích mái, sân thượng', 'Thép: hãng, loại', 'Xi măng, cát, đá: loại', 'Gạch: mã, kích thước', 'Điện nước: hãng dây, ống', 'Chống thấm: vật liệu, vị trí', 'Tiến độ và lịch thanh toán'];
    var cols = ['a', 'b', 'c'], names = { a: 'A', b: 'B', c: 'C' };
    var defaults = { a: [7], b: [0, 1, 2, 4, 7], c: [0, 1, 2, 3, 4, 5, 7] };
    var prices = { a: 5.2, b: 5.8, c: 6.1 };
    var html = '';
    rows.forEach(function(r, i){
      html += '<tr><td>' + r + '</td>';
      cols.forEach(function(c){ html += '<td class="c"><input type="checkbox" id="cmp-' + c + '-' + i + '"' + (defaults[c].indexOf(i) > -1 ? ' checked' : '') + ' aria-label="Báo giá ' + names[c] + ': ' + r + '"></td>'; });
      html += '</tr>';
    });
    html += '<tr class="cmp-sum"><td>Số mục ghi rõ</td>' + cols.map(function(c){ return '<td class="c" id="cmp-count-' + c + '"></td>'; }).join('') + '</tr>';
    html += '<tr><td>Đơn giá (triệu/m²)</td>' + cols.map(function(c){ return '<td class="c" id="cmp-pcell-' + c + '"><input type="number" id="cmp-price-' + c + '" value="' + prices[c] + '" min="0" step="0.1" inputmode="decimal" aria-label="Đơn giá báo giá ' + names[c] + '"></td>'; }).join('') + '</tr>';
    body.innerHTML = html;
    var msg = $('cmp-msg');
    var renderCmp = function() {
      var missing = [];
      cols.forEach(function(c){
        var n = 0; rows.forEach(function(r, i){ if ($('cmp-' + c + '-' + i).checked) n++; });
        $('cmp-count-' + c).textContent = n + '/' + rows.length;
        if (n < rows.length) missing.push(names[c]);
        $('cmp-pcell-' + c).classList.remove('is-best');
      });
      msg.className = 'pot-msg';
      if (missing.length) {
        msg.classList.add('is-over');
        msg.textContent = 'Báo giá ' + missing.join(', ') + ' còn mục chưa ghi rõ, nên chưa so được đơn giá. Gửi lại cho cả ba nhà thầu cùng một bộ bản vẽ và cùng một danh mục vật tư.';
      } else {
        cols.forEach(function(c){ var p = parseFloat($('cmp-price-' + c).value); prices[c] = isFinite(p) ? p : Infinity; });
        var best = cols.reduce(function(m, c){ return prices[c] < prices[m] ? c : m; }, 'a');
        $('cmp-pcell-' + best).classList.add('is-best');
        msg.classList.add('is-good');
        msg.textContent = 'Cả ba báo giá đã cùng một danh sách. Giờ mới so được: báo giá ' + names[best] + ' thấp nhất. Trước khi chọn, hãy đến xem công trình thật nhà thầu đó đã làm.';
      }
    };
    body.addEventListener('change', renderCmp);
    body.addEventListener('input', renderCmp);
    renderCmp();
  }

  /* ---------- Công cụ: đặt tên tệp ---------- */
  if ($('fn-out')) {
    $('fn-ngay').value = todayISO();
    var slug = function(s){ return fold(s).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); };
    var renderFn = function(){
      var name = slug($('fn-hang-muc').value) || 'hang-muc';
      var day = $('fn-ngay').value || todayISO();
      var v = parseInt($('fn-ban').value, 10); v = isFinite(v) && v > 0 ? v : 1;
      $('fn-out').textContent = name + '_' + day + '_v' + v + '_' + $('fn-tt').value;
    };
    ['fn-hang-muc', 'fn-ngay', 'fn-ban', 'fn-tt'].forEach(function(id){ var el = $(id); el.addEventListener('input', renderFn); el.addEventListener('change', renderFn); });
    renderFn();
    $('fn-copy').addEventListener('click', function(){ copyText($('fn-out').textContent, $('fn-status'), $('fn-fb-wrap'), $('fn-fb'), 'Đã sao chép tên tệp.'); });
  }

  /* ---------- Công cụ: nhật ký hai phút ---------- */
  if ($('log-out')) {
    $('log-ngay').value = todayISO();
    var renderLog = function(){
      var val = $('log-ngay').value || todayISO();
      var parts = val.split('-'), d = new Date(+parts[0], +parts[1] - 1, +parts[2]);
      var day = isNaN(d) ? val : d.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
      var lines = [
        'Nhật ký công trình · ' + day,
        'Thời tiết: ' + $('log-troi').value + ' · Số thợ: ' + ($('log-tho').value || '0'),
        'Hôm nay làm: ' + ($('log-viec').value.trim() || '…'),
        'Cần nhớ: ' + ($('log-ghi').value.trim() || '…'),
        'Ảnh: (đính kèm)'
      ];
      $('log-out').textContent = lines.join('\n');
    };
    ['log-ngay', 'log-troi', 'log-tho', 'log-viec', 'log-ghi'].forEach(function(id){ var el = $(id); el.addEventListener('input', renderLog); el.addEventListener('change', renderLog); });
    renderLog();
    $('log-copy').addEventListener('click', function(){ copyText($('log-out').textContent, $('log-status'), $('log-fb-wrap'), $('log-fb'), 'Đã sao chép. Dán vào sổ ghi chú hoặc nhóm chat của gia đình.'); });
  }

  /* ---------- Công cụ: bản mô tả nhu cầu ---------- */
  var qs = Array.prototype.slice.call(document.querySelectorAll('.need-q'));
  if (qs.length && $('copy-needs')) {
    var KEY = 'shanco-nhu-cau-v1';
    var savedNeeds = store(KEY) || {};
    qs.forEach(function(t){ if (savedNeeds[t.id]) t.value = savedNeeds[t.id]; });
    var saveNeeds = function(){ var o = {}; qs.forEach(function(x){ o[x.id] = x.value; }); store(KEY, o); };
    qs.forEach(function(t){ t.addEventListener('input', saveNeeds); });
    var buildBrief = function(){
      var lines = ['BẢN MÔ TẢ NHU CẦU', ''];
      qs.forEach(function(t){
        var lab = document.querySelector('label[for="' + t.id + '"]');
        lines.push(lab ? lab.textContent : '');
        lines.push(t.value.trim() || '(chưa trả lời)');
        lines.push('');
      });
      return lines.join('\n').trim();
    };
    $('copy-needs').addEventListener('click', function(){ copyText(buildBrief(), $('needs-status'), $('needs-out-wrap'), $('nhu-cau-out'), 'Đã sao chép. Bạn có thể dán vào tin nhắn gửi kiến trúc sư.'); });
    var clearBtn = $('clear-needs'), armed = false, armTimer;
    if (clearBtn) clearBtn.addEventListener('click', function(){
      if (!armed) {
        armed = true; clearBtn.textContent = 'Bấm lần nữa để xoá';
        clearTimeout(armTimer); armTimer = setTimeout(function(){ armed = false; clearBtn.textContent = 'Xoá câu trả lời'; }, 3500);
        return;
      }
      armed = false; clearTimeout(armTimer); clearBtn.textContent = 'Xoá câu trả lời';
      qs.forEach(function(t){ t.value = ''; }); saveNeeds();
      $('needs-out-wrap').hidden = true; $('needs-status').textContent = 'Đã xoá các câu trả lời.';
    });
  }

  /* ---------- Công cụ: nồi canh ngân sách ---------- */
  if ($('tien-co') && $('pot-msg')) {
    var fmt = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });
    var num = function(id){ var v = parseFloat(String($(id).value).replace(',', '.')); return isFinite(v) && v > 0 ? v : 0; };
    var money = function(v){ return fmt.format(Math.round(v * 10) / 10) + ' triệu'; };
    var H = 172, BOTTOM = 254, TOP = 82;
    var setLayer = function(id, from, h){ var r = $(id); r.setAttribute('y', BOTTOM - from - h); r.setAttribute('height', Math.max(0, h)); };
    var renderPot = function(){
      var budget = num('tien-co'), build = num('dien-tich') * num('don-gia');
      var extras = num('noi-that') + num('cong-san') + num('thiet-ke');
      var pct = num('du-phong'), reserve = (build + extras) * pct / 100, total = build + extras + reserve;
      $('du-phong-out').textContent = pct + '%';
      $('lg-build').textContent = money(build); $('lg-extra').textContent = money(extras);
      $('lg-res').textContent = money(reserve); $('lg-total').textContent = money(total); $('lg-budget').textContent = money(budget);
      var s = budget > 0 ? H / budget : 0, hb = build * s, he = extras * s, hr = reserve * s;
      if (budget <= 0) { hb = he = hr = 0; }
      setLayer('ly-build', 0, hb); setLayer('ly-extra', hb, he); setLayer('ly-res', hb + he, hr);
      var over = budget > 0 && total > budget, topY = BOTTOM - total * s;
      var line = $('ly-top'), lab = $('ly-top-label'), showLine = !over && budget > 0 && topY > TOP + 14;
      line.setAttribute('y1', topY); line.setAttribute('y2', topY);
      lab.setAttribute('y', Math.max(TOP + 16, topY - 6));
      line.classList.toggle('is-off', !showLine); lab.classList.toggle('is-off', !showLine);
      $('pot-spill').classList.toggle('is-off', !over);
      var msg = $('pot-msg');
      msg.className = 'pot-msg';
      if (budget <= 0) msg.textContent = 'Nhập số tiền nhà mình có để xem nồi đầy đến đâu.';
      else if (over) { msg.classList.add('is-over'); msg.textContent = 'Nồi tràn mất ' + money(total - budget) + '. Thử bớt một khoản, chọn mức hoàn thiện khác, hoặc chuẩn bị thêm tiền trước khi khởi công.'; }
      else if (pct === 0) msg.textContent = 'Vừa đủ, nhưng chưa chừa chỗ để nêm. Chỉ một khoản phát sinh nhỏ cũng có thể làm nồi tràn.';
      else { msg.classList.add('is-good'); msg.textContent = 'Nồi còn chỗ để nêm: dự phòng ' + money(reserve) + ', và còn trống thêm ' + money(budget - total) + '.'; }
    };
    ['tien-co', 'dien-tich', 'don-gia', 'noi-that', 'cong-san', 'thiet-ke', 'du-phong'].forEach(function(id){ $(id).addEventListener('input', renderPot); });
    renderPot();
  }

  /* ---------- Từ điển chạm-là-hiện ---------- */
  var pop = null;
  function closePop() { if (pop) { pop.remove(); pop = null; } document.querySelectorAll('a.term[aria-expanded="true"]').forEach(function(a){ a.setAttribute('aria-expanded', 'false'); }); }
  document.addEventListener('click', function(e){
    var a = e.target.closest && e.target.closest('a.term');
    if (!a) { if (pop && !(e.target.closest && e.target.closest('.term-pop'))) closePop(); return; }
    if (a.getAttribute('aria-expanded') === 'true') return; /* bấm lần hai: mở trang từ điển */
    e.preventDefault(); closePop();
    pop = document.createElement('div');
    pop.className = 'term-pop'; pop.setAttribute('role', 'note');
    var b = document.createElement('b'); b.textContent = a.dataset.term || a.textContent;
    var t = document.createElement('span'); t.textContent = ' ' + (a.dataset.def || '') + ' ';
    var more = document.createElement('a'); more.href = a.getAttribute('href'); more.textContent = 'Xem trong từ điển →';
    pop.appendChild(b); pop.appendChild(t); pop.appendChild(more);
    document.body.appendChild(pop);
    var r = a.getBoundingClientRect(), w = pop.offsetWidth;
    var left = Math.min(Math.max(16, r.left + window.scrollX), window.scrollX + document.documentElement.clientWidth - w - 16);
    pop.style.left = left + 'px'; pop.style.top = (r.bottom + window.scrollY + 8) + 'px';
    a.setAttribute('aria-expanded', 'true');
  });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closePop(); });

  /* ---------- Tìm kiếm ---------- */
  var out = $('search-results');
  if (out) {
    var input = $('q'), status = $('search-status');
    var params = new URLSearchParams(location.search);
    input.value = params.get('q') || '';
    var order = ['hoi-nhanh', 'cong-cu', 'cam-nang', 'tu-dien', 'truyen', 'chuyen-sau', 'chang', 'trang'];
    var labels = { 'hoi-nhanh': 'Trả lời nhanh', 'cong-cu': 'Công cụ', 'cam-nang': 'Cẩm nang', 'tu-dien': 'Từ điển', 'truyen': 'Truyện', 'chuyen-sau': 'Chuyên sâu', 'chang': 'Chặng', 'trang': 'Trang khác' };
    var esc = function(s){ return String(s).replace(/[&<>"]/g, function(c){ return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
    var run = function(index){
      var q = fold(input.value).trim();
      if (!q) { out.innerHTML = ''; status.textContent = ''; $('search-empty').hidden = true; return; }
      var words = q.split(/\s+/).filter(function(w){ return w.length > 1 || /\d/.test(w); });
      if (!words.length) words = [q];
      var hits = index.map(function(it){
        var t = fold(it.t), x = it.x, sc = 0;
        for (var i = 0; i < words.length; i++) {
          var w = words[i];
          if (t.indexOf(w) > -1) sc += 3; else if (x.indexOf(w) > -1) sc += 1; else return null;
        }
        if (t.indexOf(q) > -1) sc += 4;
        return { it: it, sc: sc };
      }).filter(Boolean).sort(function(a, b){ return b.sc - a.sc; });
      var groups = {};
      hits.forEach(function(h){ (groups[h.it.k] = groups[h.it.k] || []).push(h.it); });
      var html = '';
      order.forEach(function(k){
        if (!groups[k]) return;
        html += '<section><h2>' + labels[k] + '</h2><ol>' + groups[k].slice(0, 8).map(function(it){
          return '<li><a href="' + it.u + '"><span class="k">' + esc(it.c || '') + '</span><span class="t">' + esc(it.t) + '</span>' + (it.s ? '<span class="p">' + esc(it.s) + '</span>' : '') + '</a></li>';
        }).join('') + '</ol></section>';
      });
      out.innerHTML = html;
      status.textContent = hits.length ? 'Tìm thấy ' + hits.length + ' kết quả cho “' + input.value.trim() + '”.' : '';
      $('search-empty').hidden = hits.length > 0;
    };
    fetch('/assets/data/tim-kiem.json').then(function(r){ return r.json(); }).then(function(index){
      run(index);
      var timer;
      input.addEventListener('input', function(){
        clearTimeout(timer);
        timer = setTimeout(function(){
          run(index);
          var u = new URL(location.href); u.searchParams.set('q', input.value); history.replaceState(null, '', u);
        }, 150);
      });
      $('search-form').addEventListener('submit', function(e){ e.preventDefault(); run(index); });
    }).catch(function(){ status.textContent = 'Chưa tải được dữ liệu tìm kiếm. Hãy thử tải lại trang.'; });
  }
})();
