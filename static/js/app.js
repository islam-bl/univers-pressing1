/* ── State ── */
let lang = 'fr';
let allOrders = [];
let currentFilter = 'all';
let currentUserRole = 'employe'; // sera mis à jour au chargement

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  loadUserInfo();
  setDates();
  buildArticleSelect();
  buildServiceSelect();
  loadDashboard();
  loadSettings();
});

/* ════ LANGUAGE ════ */
function toggleLang() {
  lang = lang === 'fr' ? 'ar' : 'fr';
  const html = document.documentElement;
  html.setAttribute('lang', lang);
  html.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
  document.getElementById('langToggle').textContent = lang === 'ar' ? '🌐 Français' : '🌐 العربية';
  document.querySelectorAll('[data-fr][data-ar]').forEach(el => {
    el.textContent = el.getAttribute(`data-${lang}`);
  });
  buildArticleSelect();
  buildServiceSelect();
}

/* ════ NAV ════ */
function showPage(page) {
  // Vérification des permissions pour les pages gérant-only
  const gerantOnlyPages = ['dashboard', 'history', 'settings', 'employees'];
  if (gerantOnlyPages.includes(page) && currentUserRole !== 'gerant') {
    showToast(lang === 'fr' ? '⛔ Accès réservé au gérant' : '⛔ هذه الصفحة للمسؤول فقط', 'error');
    return;
  }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');
  const nb = document.getElementById(`nav-${page}`);
  if (nb) nb.classList.add('active');
  document.getElementById('sidebar').classList.remove('open');
  if (page === 'dashboard') loadDashboard();
  if (page === 'orders')    loadOrders();
  if (page === 'history')   loadHistory();
  if (page === 'settings')  loadSettings();
  if (page === 'employees') loadEmployees();
}
function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

/* ════ USER / ROLE ════ */
async function loadUserInfo() {
  try {
    const r = await fetch('/api/auth/me');
    if (r.ok) {
      const d = await r.json();
      if (d.logged_in) {
        currentUserRole = d.role || 'employe';
        document.getElementById('userName').textContent = d.full_name;
        document.getElementById('userAvatar').textContent = d.full_name.charAt(0).toUpperCase();
        // Affiche le rôle sous le nom
        const roleEl = document.getElementById('userRole');
        if (roleEl) {
          roleEl.textContent = currentUserRole === 'gerant'
            ? (lang === 'fr' ? 'Gérant' : 'مسؤول')
            : (lang === 'fr' ? 'Employé' : 'موظف');
        }
        applyRoleRestrictions();
        // Si employé, rediriger vers commandes (pas dashboard)
        if (currentUserRole !== 'gerant') {
          // Cacher dashboard, montrer orders
          document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
          document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
          const ordersPage = document.getElementById('page-orders');
          const ordersNav = document.getElementById('nav-orders');
          if (ordersPage) ordersPage.classList.add('active');
          if (ordersNav) ordersNav.classList.add('active');
          loadOrders();
        }
      }
    }
  } catch(e) {}
}

function applyRoleRestrictions() {
  // Cacher les éléments réservés au gérant si l'utilisateur est employé
  const gerantOnly = document.querySelectorAll('.gerant-only');
  gerantOnly.forEach(el => {
    el.style.display = currentUserRole === 'gerant' ? '' : 'none';
  });
}

async function doLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}

/* ════ DEPOSIT FORM ════ */
function setDates() {
  const today = new Date().toISOString().split('T')[0];
  const fut = new Date(); fut.setDate(fut.getDate() + 3);
  document.getElementById('depositDate').value = today;
  document.getElementById('pickupDateInput').value = fut.toISOString().split('T')[0];
}

function buildArticleSelect() {
  const sel = document.getElementById('articleSelect');
  const cur = sel.value;
  const placeholder = lang === 'fr' ? '-- Choisir l\'article --' : '-- اختر القطعة --';
  sel.innerHTML = `<option value="">${placeholder}</option>`;
  Object.entries(CATALOG).forEach(([k, v]) => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.textContent = `${v.fr} / ${v.ar}`;
    if (k === cur) opt.selected = true;
    sel.appendChild(opt);
  });
}

function buildServiceSelect() {
  const sel = document.getElementById('serviceSelect');
  const cur = sel.value;
  const placeholder = lang === 'fr' ? '-- Choisir le service --' : '-- اختر الخدمة --';
  sel.innerHTML = `<option value="">${placeholder}</option>`;
  Object.entries(SERVICES).forEach(([k, v]) => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.textContent = `${v.fr} / ${v.ar}`;
    if (k === cur) opt.selected = true;
    sel.appendChild(opt);
  });
}

function updatePrice() {
  const article = document.getElementById('articleSelect').value;
  const service = document.getElementById('serviceSelect').value;
  const pd = document.getElementById('priceDisplay');
  const highVal = document.getElementById('highValueToggle').checked;

  if (article && service) {
    const art = CATALOG[article];
    if (!art) { pd.style.display = 'none'; return; }

    let priceText = 'N/D';
    let priceNum = null;

    if (service === 'nettoyage_repassage') {
      const n = art.nettoyage;
      const r = art.repassage;
      if (n !== null && n !== undefined && r !== null && r !== undefined) {
        const nMin = typeof n === 'object' ? n.min : n;
        const total = nMin + r;
        const nDisplay = typeof n === 'object' ? `${n.min}-${n.max}` : n;
        priceText = `${total.toFixed(2)} DH (تصبين ${nDisplay} + تحديد ${r})`;
        priceNum = total;
      } else {
        priceText = 'N/D (service non disponible)';
      }
    } else {
      const p = art[service];
      if (p !== null && p !== undefined) {
        if (typeof p === 'object') {
          priceText = `${p.min} à ${p.max} DH`;
          priceNum = p.min;
        } else {
          priceText = `${p.toFixed(2)} DH`;
          priceNum = p;
        }
      } else {
        priceText = 'N/D (service non disponible)';
      }
    }

    pd.style.display = 'flex';
    document.getElementById('catalogPrice').textContent = priceText;
    if (!highVal && priceNum !== null) {
      document.getElementById('finalPriceInput').value = priceNum.toFixed(2);
    }
  } else {
    pd.style.display = 'none';
  }
  updateOrderTotal();
}

function toggleHighValue() {
  const on = document.getElementById('highValueToggle').checked;
  document.getElementById('manualPriceGroup').style.display = on ? 'block' : 'none';
  document.getElementById('priceOverrideHidden').value = on ? '1' : '0';
  if (!on) updatePrice();
}

function previewPhoto(input) {
  if (input.files && input.files[0]) {
    const r = new FileReader();
    r.onload = e => {
      document.getElementById('photoPreview').src = e.target.result;
      document.getElementById('photoPreview').style.display = 'block';
      document.getElementById('photoIcon').style.display = 'none';
      document.getElementById('photoText').style.display = 'none';
    };
    r.readAsDataURL(input.files[0]);
  }
}

document.getElementById('depositForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;margin:0 auto"></div>';

  const form = e.target;
  const fd = new FormData();

  // Champs client / commande (une seule fois)
  fd.append('customer_name',              form.customer_name.value);
  fd.append('customer_phone',             form.customer_phone.value);
  fd.append('deposit_date',               form.deposit_date.value);
  fd.append('expected_pickup_date',       form.expected_pickup_date.value);
  fd.append('authorized_person_name',     form.authorized_person_name?.value || '');
  fd.append('authorized_person_relation', form.authorized_person_relation?.value || '');
  fd.append('notes',                      form.notes?.value || '');
  const photoInput = form.article_photo;
  if (photoInput && photoInput.files && photoInput.files[0]) {
    fd.append('article_photo', photoInput.files[0]);
  }

  // Construire la liste d'articles (article principal + articles supplémentaires)
  const items = [];
  const mainArt = document.getElementById('articleSelect').value;
  const mainSvc = document.getElementById('serviceSelect').value;
  const highVal = document.getElementById('highValueToggle').checked;
  if (mainArt && mainSvc) {
    let mainPrice;
    if (highVal) mainPrice = parseFloat(document.getElementById('finalPriceInput').value) || 0;
    else         mainPrice = getPrice(mainArt, mainSvc) || 0;
    items.push({
      article_type: mainArt,
      service_type: mainSvc,
      is_high_value: highVal ? 1 : 0,
      price_overridden: highVal ? 1 : 0,
      final_price: mainPrice,
      notes: form.notes?.value || ''
    });
  }
  document.querySelectorAll('[id^="extraArticle_"]').forEach(el => {
    const idx = el.id.split('_')[1];
    const a = document.getElementById(`extraArticleSelect_${idx}`)?.value;
    const s = document.getElementById(`extraServiceSelect_${idx}`)?.value;
    if (!a || !s) return;
    const n = el.querySelector(`[name="extra_notes_${idx}"]`)?.value || '';
    items.push({
      article_type: a,
      service_type: s,
      is_high_value: 0,
      price_overridden: 0,
      final_price: getPrice(a, s) || 0,
      notes: n
    });
  });

  if (items.length === 0) {
    showToast(lang === 'fr' ? 'Ajoutez au moins un article' : 'أضف قطعة واحدة على الأقل', 'error');
    btn.disabled = false;
    btn.innerHTML = `<span>${lang === 'fr' ? 'Enregistrer le Dépôt' : 'حفظ الإيداع'}</span>`;
    return;
  }

  fd.append('items', JSON.stringify(items));

  try {
    const r = await fetch('/api/orders', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.success) {
      showMultiReceiptModal(d.order, [], d.whatsapp_msg);
      form.reset();
      setDates();
      buildServiceSelect();
      document.getElementById('photoPreview').style.display = 'none';
      document.getElementById('photoIcon').style.display = 'block';
      document.getElementById('photoText').style.display = 'block';
      document.getElementById('priceDisplay').style.display = 'none';
      document.getElementById('manualPriceGroup').style.display = 'none';
      document.getElementById('extraArticlesContainer').innerHTML = '';
      extraArticleCount = 0;
      const totalDisplay = document.getElementById('orderTotalDisplay');
      if (totalDisplay) totalDisplay.style.display = 'none';
      showToast(lang === 'fr' ? `✅ Commande enregistrée (${items.length} article(s)) !` : `✅ تم تسجيل الطلب (${items.length} قطعة) !`, 'success');
    } else {
      showToast('Erreur: ' + (d.error || ''), 'error');
    }
  } catch(ex) {
    showToast('Erreur réseau', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span data-fr="Enregistrer le Dépôt" data-ar="حفظ الإيداع">${lang === 'fr' ? 'Enregistrer le Dépôt' : 'حفظ الإيداع'}</span>`;
  }
});
function updateOrderTotal() {
  // Calcul du prix de l'article principal
  const mainArt = document.getElementById('articleSelect').value;
  const mainSvc = document.getElementById('serviceSelect').value;
  const highVal = document.getElementById('highValueToggle').checked;
  let mainPrice = 0;
  if (highVal) {
    mainPrice = parseFloat(document.getElementById('finalPriceInput').value) || 0;
  } else if (mainArt && mainSvc) {
    mainPrice = getPrice(mainArt, mainSvc) || 0;
  }

  // Calcul des prix des articles supplémentaires
  let extrasTotal = 0;
  const extras = document.querySelectorAll('[id^="extraArticle_"]');
  extras.forEach(el => {
    const idx = el.id.split('_')[1];
    const artV = document.getElementById(`extraArticleSelect_${idx}`)?.value;
    const svcV = document.getElementById(`extraServiceSelect_${idx}`)?.value;
    if (artV && svcV) extrasTotal += getPrice(artV, svcV) || 0;
  });

  const total = mainPrice + extrasTotal;
  const totalEl = document.getElementById('orderTotalDisplay');
  if (totalEl) {
    if (extras.length > 0 || (mainArt && mainSvc)) {
      totalEl.style.display = 'flex';
      document.getElementById('orderTotalAmount').textContent = total.toFixed(2) + ' MAD';
    } else {
      totalEl.style.display = 'none';
    }
  }
}



/* ════ ARTICLES SUPPLÉMENTAIRES ════ */
// Compteur pour les articles supplémentaires
let extraArticleCount = 0;

/**
 * Ajoute un bloc article/service supplémentaire dans le formulaire de dépôt.
 * Permet d'enregistrer plusieurs articles pour le même client en une seule commande.
 */
function addExtraArticle() {
  extraArticleCount++;
  const idx = extraArticleCount;

  // Construction des options article depuis le catalogue
  let articleOpts = `<option value="">-- ${lang === 'fr' ? "Choisir l'article" : "اختر القطعة"} --</option>`;
  Object.entries(CATALOG).forEach(([k, v]) => {
    articleOpts += `<option value="${k}">${v.fr} / ${v.ar}</option>`;
  });

  // Construction des options service
  let serviceOpts = `<option value="">-- ${lang === 'fr' ? 'Choisir le service' : 'اختر الخدمة'} --</option>`;
  Object.entries(SERVICES).forEach(([k, v]) => {
    serviceOpts += `<option value="${k}">${v.fr} / ${v.ar}</option>`;
  });

  const html = `
    <div class="form-section" id="extraArticle_${idx}" style="border:2px dashed var(--border);border-radius:var(--radius);padding:16px;margin-bottom:12px;position:relative">
      <div class="form-section-title">
        <div class="section-badge">👔</div>
        <span>${lang === 'fr' ? 'Article supplémentaire' : 'قطعة إضافية'} #${idx}</span>
        <button type="button" onclick="removeExtraArticle(${idx})" style="margin-left:auto;background:none;border:none;color:var(--danger);cursor:pointer;font-size:1.2rem">✕</button>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label>${lang === 'fr' ? "Type d'article *" : "نوع القطعة *"}</label>
          <select name="extra_article_type_${idx}" id="extraArticleSelect_${idx}" class="form-input" onchange="updateExtraPrice(${idx})">${articleOpts}</select>
        </div>
        <div class="form-group">
          <label>${lang === 'fr' ? 'Service *' : 'الخدمة *'}</label>
          <select name="extra_service_type_${idx}" id="extraServiceSelect_${idx}" class="form-input" onchange="updateExtraPrice(${idx})">${serviceOpts}</select>
        </div>
      </div>
      <div id="extraPriceDisplay_${idx}" style="display:none;background:var(--accent-light);border-radius:var(--radius-sm);padding:10px 14px;margin-top:8px;font-size:.9rem;color:var(--primary);font-weight:600">
        💰 ${lang === 'fr' ? 'Prix' : 'السعر'} : <span id="extraCatalogPrice_${idx}"></span>
      </div>
      <div class="form-group" style="margin-top:10px">
        <label>${lang === 'fr' ? 'Notes (optionnel)' : 'ملاحظات (اختياري)'}</label>
        <input type="text" name="extra_notes_${idx}" class="form-input" placeholder="${lang === 'fr' ? 'Taches, couleur...' : 'بقع، لون...'}"/>
      </div>
    </div>`;

  document.getElementById('extraArticlesContainer').insertAdjacentHTML('beforeend', html);
  updateOrderTotal();
}

/**
 * Met à jour le prix affiché pour un article supplémentaire.
 */
function updateExtraPrice(idx) {
  const article = document.getElementById(`extraArticleSelect_${idx}`).value;
  const service = document.getElementById(`extraServiceSelect_${idx}`).value;
  const pd = document.getElementById(`extraPriceDisplay_${idx}`);
  if (!article || !service) { pd.style.display = 'none'; return; }
  const art = CATALOG[article];
  if (!art) { pd.style.display = 'none'; return; }
  let priceText = 'N/D';
  if (service === 'nettoyage_repassage') {
    const n = art.nettoyage, r = art.repassage;
    if (n != null && r != null) {
      const nMin = typeof n === 'object' ? n.min : n;
      const nDisplay = typeof n === 'object' ? `${n.min}-${n.max}` : n;
      priceText = `${(nMin + r).toFixed(2)} DH`;
    }
  } else {
    const p = art[service];
    if (p != null) priceText = typeof p === 'object' ? `${p.min}-${p.max} DH` : `${p.toFixed(2)} DH`;
  }
  pd.style.display = 'flex';
  document.getElementById(`extraCatalogPrice_${idx}`).textContent = priceText;
  updateOrderTotal();
}

/**
 * Supprime un bloc article supplémentaire du formulaire.
 */
function removeExtraArticle(idx) {
  const el = document.getElementById(`extraArticle_${idx}`);
  if (el) el.remove();
  updateOrderTotal();
}

/* ════ RECEIPT MODAL ════ */
function showReceiptModal(order, waMsg) {
  const art = CATALOG[order.article_type] || {};
  const artL = art[lang === 'fr' ? 'fr' : 'ar'] || order.article_type;
  const svcL = SERVICES[order.service_type]?.[lang === 'fr' ? 'fr' : 'ar'] || order.service_type;
  const phone = order.customer_phone?.replace(/\D/g,'') || '';
  const waLink = `https://wa.me/${phone.startsWith('0') ? '212' + phone.slice(1) : phone}?text=${encodeURIComponent(waMsg || '')}`;

  // Calcul du total : somme de tous les articles de la commande (et pas seulement le premier).
  const items = Array.isArray(order.items) ? order.items : [];
  const totalAmount = items.length > 0
    ? items.reduce((sum, it) => sum + (parseFloat(it.final_price) || 0), 0)
    : (parseFloat(order.final_price) || 0);

  // Lignes détaillées par article (affichées seulement s'il y a 2 articles ou plus).
  const itemsRows = items.length > 1 ? items.map((it, i) => {
    const a = CATALOG[it.article_type] || {};
    const aL = it.article_fr || a[lang === 'fr' ? 'fr' : 'ar'] || it.article_type;
    const sL = it.service_fr || SERVICES[it.service_type]?.[lang === 'fr' ? 'fr' : 'ar'] || it.service_type;
    return `<div class="receipt-row"><span class="receipt-label">${i + 1}. ${aL} — ${sL}</span><span class="receipt-val">${(parseFloat(it.final_price) || 0).toFixed(2)} MAD</span></div>`;
  }).join('') : '';

  const html = `
    <div>
      <!-- Zone imprimable UNIQUEMENT -->
      <div class="receipt" id="printZone">
        <div class="receipt-header">
          <div class="receipt-logo-wrap"><img src="/static/images/logo.png" alt="Logo"/></div>
          <div class="receipt-company">Univers Pressing</div>
          <div class="receipt-company-ar">عالم التصبين</div>
          <div class="receipt-order">${order.order_number}</div>
          <div style="font-size:.82rem;color:var(--text-mid);margin-bottom:4px">${lang==='fr'?'Code de retrait':'رمز الاستلام'}</div>
          <div class="pickup-code-badge">${order.pickup_code}</div>
        </div>
        <div class="receipt-row"><span class="receipt-label">${lang==='fr'?'Client':'الزبون'}</span><span class="receipt-val">${order.customer_name}</span></div>
        <div class="receipt-row"><span class="receipt-label">${lang==='fr'?'Téléphone':'رقم الهاتف'}</span><span class="receipt-val">${order.customer_phone}</span></div>
        <div class="receipt-row"><span class="receipt-label">${lang==='fr'?'Article':'القطعة'}</span><span class="receipt-val">${artL}</span></div>
        <div class="receipt-row"><span class="receipt-label">${lang==='fr'?'Type de service':'نوع الخدمة'}</span><span class="receipt-val">${svcL}</span></div>
        ${itemsRows}
        <div class="receipt-row"><span class="receipt-label">${lang==='fr'?'Date de dépôt':'تاريخ الاستلام'}</span><span class="receipt-val">${order.deposit_date}</span></div>
        <div class="receipt-row"><span class="receipt-label">${lang==='fr'?'Date de retrait':'تاريخ التسليم'}</span><span class="receipt-val">${order.expected_pickup_date}</span></div>
        <div class="receipt-total"><div style="font-size:.8rem;opacity:.7">${lang==='fr'?'MONTANT TOTAL':'المبلغ الإجمالي'}</div><div class="receipt-total-amt">${totalAmount.toFixed(2)} MAD</div></div>
      </div>

      <!-- Zone WhatsApp — exclue de l'impression -->
      <div class="no-print">
        ${waMsg ? `<div class="whatsapp-cta" style="margin-top:14px">
          <p>💬 ${lang==='fr'?'Message prêt à envoyer au client :':'الرسالة جاهزة للإرسال :'}</p>
          <div class="whatsapp-msg">${waMsg}</div>
          <div class="whatsapp-btns">
            <button class="btn btn-success" onclick="window.open('${waLink}','_blank')">📱 WhatsApp</button>
            <button class="btn btn-ghost" onclick="navigator.clipboard.writeText(${JSON.stringify(waMsg)});showToast('${lang==='fr'?'Copié !':'تم النسخ !'}','success')">📋 ${lang==='fr'?'Copier':'نسخ'}</button>
          </div>
        </div>` : ''}
        <div style="display:flex;gap:10px;margin-top:14px">
          <button class="btn btn-primary btn-full" onclick="printReceipt()">🖨️ ${lang==='fr'?'Imprimer':'طباعة'}</button>
          <button class="btn btn-ghost btn-full" onclick="closeModal()">${lang==='fr'?'Fermer':'إغلاق'}</button>
        </div>
      </div>
    </div>`;
  openModal(html);
}


/* ════ REÇU MULTI-ARTICLES ════ */
/**
 * Affiche un reçu combiné pour plusieurs articles du même client.
 * Calcule le total général de tous les articles.
 * - mainOrder : la commande principale
 * - extraOrders : tableau des commandes supplémentaires
 * - waMsg : message WhatsApp de la commande principale
 */
function showMultiReceiptModal(mainOrder, extraOrders, waMsg) {
  // Si pas d'articles supplémentaires, afficher le reçu simple
  if (!extraOrders || extraOrders.length === 0) {
    showReceiptModal(mainOrder, waMsg);
    return;
  }

  // Regrouper tous les articles (principal + supplémentaires)
  const allOrders = [mainOrder, ...extraOrders];

  // Calcul du total général
  const total = allOrders.reduce((sum, o) => sum + parseFloat(o.final_price || 0), 0);

  // Construire les lignes du reçu pour chaque article
  const articleRows = allOrders.map((o, i) => {
    const art = CATALOG[o.article_type] || {};
    const artL = o.article_fr || art[lang === 'fr' ? 'fr' : 'ar'] || o.article_type;
    const svcL = o.service_fr || SERVICES[o.service_type]?.[lang === 'fr' ? 'fr' : 'ar'] || '';
    return `
      <div style="background:var(--bg);border-radius:8px;padding:10px 12px;margin-bottom:8px;border-left:3px solid var(--primary)">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-weight:700;font-size:.9rem;color:var(--navy)">${i + 1}. ${artL}</div>
            <div style="font-size:.8rem;color:var(--text-mid)">${svcL} · Code: <b>${o.pickup_code}</b></div>
          </div>
          <div style="font-weight:800;color:var(--primary);font-size:1rem">${parseFloat(o.final_price || 0).toFixed(2)} MAD</div>
        </div>
      </div>`;
  }).join('');

  // Préparer le lien WhatsApp avec le total
  const phone = mainOrder.customer_phone?.replace(/\D/g, '') || '';
  const waPhone = phone.startsWith('0') ? '212' + phone.slice(1) : phone;
  const waLink = `https://wa.me/${waPhone}?text=${encodeURIComponent(waMsg || '')}`;

  const html = `
    <div>
      <div class="receipt" id="printZone">
        <div class="receipt-header">
          <div class="receipt-logo-wrap"><img src="/static/images/logo.png" alt="Logo"/></div>
          <div class="receipt-company">Univers Pressing</div>
          <div class="receipt-company-ar">عالم التصبين</div>
          <div class="receipt-order">${lang === 'fr' ? 'Dépôt multiple' : 'إيداع متعدد'}</div>
        </div>
        <div class="receipt-row">
          <span class="receipt-label">${lang === 'fr' ? 'Client' : 'الزبون'}</span>
          <span class="receipt-val">${mainOrder.customer_name}</span>
        </div>
        <div class="receipt-row">
          <span class="receipt-label">${lang === 'fr' ? 'Téléphone' : 'رقم الهاتف'}</span>
          <span class="receipt-val">${mainOrder.customer_phone}</span>
        </div>
        <div class="receipt-row">
          <span class="receipt-label">${lang === 'fr' ? 'Date dépôt' : 'تاريخ الإيداع'}</span>
          <span class="receipt-val">${mainOrder.deposit_date}</span>
        </div>
        <div class="receipt-row">
          <span class="receipt-label">${lang === 'fr' ? 'Retrait prévu' : 'الاستلام المتوقع'}</span>
          <span class="receipt-val">${mainOrder.expected_pickup_date}</span>
        </div>

        <!-- Liste des articles avec prix individuels -->
        <div style="margin:14px 0 8px;font-weight:700;font-size:.85rem;color:var(--navy);text-transform:uppercase;letter-spacing:.05em">
          ${lang === 'fr' ? `${allOrders.length} Articles` : `${allOrders.length} قطع`}
        </div>
        ${articleRows}

        <!-- Total général -->
        <div class="receipt-total">
          <div style="font-size:.8rem;opacity:.7">${lang === 'fr' ? 'TOTAL GÉNÉRAL' : 'المجموع الكلي'}</div>
          <div class="receipt-total-amt">${total.toFixed(2)} MAD</div>
        </div>
      </div>

      <!-- Boutons WhatsApp et actions -->
      <div class="no-print">
        ${waMsg ? `<div class="whatsapp-cta" style="margin-top:14px">
          <p>💬 ${lang === 'fr' ? 'Message prêt à envoyer au client :' : 'الرسالة جاهزة للإرسال :'}</p>
          <div class="whatsapp-msg">${waMsg}</div>
          <div class="whatsapp-btns">
            <button class="btn btn-success" onclick="window.open('${waLink}','_blank')">📱 WhatsApp</button>
            <button class="btn btn-ghost" onclick="navigator.clipboard.writeText(${JSON.stringify(waMsg)});showToast('${lang === 'fr' ? 'Copié !' : 'تم النسخ !'}','success')">📋 ${lang === 'fr' ? 'Copier' : 'نسخ'}</button>
          </div>
        </div>` : ''}
        <div style="display:flex;gap:10px;margin-top:14px">
          <button class="btn btn-primary btn-full" onclick="printReceipt()">🖨️ ${lang === 'fr' ? 'Imprimer' : 'طباعة'}</button>
          <button class="btn btn-ghost btn-full" onclick="closeModal()">${lang === 'fr' ? 'Fermer' : 'إغلاق'}</button>
        </div>
      </div>
    </div>`;
  openModal(html);
}

function printReceipt() {
  const printContent = document.getElementById('printZone').innerHTML;
  const w = window.open('','_blank','width=500,height=700');
  w.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>Reçu — Univers Pressing</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Plus Jakarta Sans',sans-serif;padding:24px;color:#1E293B}
    .receipt-header{text-align:center;border-bottom:2px dashed #E2E8F0;padding-bottom:16px;margin-bottom:16px}
    .receipt-logo-wrap{width:60px;height:60px;background:#EDE9FE;border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 10px;overflow:hidden}
    .receipt-logo-wrap img{width:50px;height:50px;object-fit:contain}
    .receipt-company{font-size:1.2rem;font-weight:800;color:#0F172A}
    .receipt-company-ar{font-size:.85rem;color:#64748B;margin-top:2px}
    .receipt-order{font-size:1.2rem;font-weight:800;color:#0F172A;margin:12px 0 4px}
    .pickup-code-badge{display:inline-block;background:#EDE9FE;border:2px solid #6C3EF4;border-radius:10px;padding:8px 20px;font-size:1.6rem;font-weight:800;letter-spacing:.18em;color:#6C3EF4;margin:4px 0}
    .receipt-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F1EFFC;font-size:.88rem}
    .receipt-label{color:#64748B;font-weight:500}
    .receipt-val{font-weight:600;color:#1E293B}
    .receipt-total{background:#0F172A;color:white;border-radius:10px;padding:12px;text-align:center;margin:14px 0}
    .receipt-total-amt{font-size:1.8rem;font-weight:800}
  </style></head><body>${printContent}</body></html>`);
  w.document.close();
  w.focus();
  setTimeout(() => { w.print(); w.close(); }, 400);
}

/* ════ DASHBOARD (gérant uniquement) ════ */
async function loadDashboard() {
  if (currentUserRole !== 'gerant') return;
  try {
    const [rec, rdy, comp] = await Promise.all([
      fetch('/api/orders?status=received').then(r=>r.json()),
      fetch('/api/orders?status=ready').then(r=>r.json()),
      fetch('/api/orders?status=completed').then(r=>r.json()),
    ]);
    document.getElementById('stat-received').textContent  = rec.length;
    document.getElementById('stat-ready').textContent     = rdy.length;
    document.getElementById('stat-completed').textContent = comp.length;
    const now = new Date(), ms = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    const rev = comp.filter(o=>o.actual_pickup_date?.startsWith(ms)).reduce((s,o)=>s+parseFloat(o.final_price||0),0);
    document.getElementById('stat-revenue').textContent = rev.toFixed(0);
    const recent = [...rec,...rdy].sort((a,b)=>new Date(b.created_at)-new Date(a.created_at)).slice(0,8);
    const el = document.getElementById('recentList');
    el.innerHTML = recent.length ? recent.map(o=>orderCardHTML(o,true)).join('') :
      `<div class="empty-state"><div class="empty-state-icon">📭</div><p>${lang==='fr'?'Aucune commande active':'لا توجد طلبات نشطة'}</p></div>`;
  } catch(e) { console.error(e); }
}

/* ════ ORDERS ════ */
async function loadOrders() {
  document.getElementById('ordersList').innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
  try {
    const [rec,rdy] = await Promise.all([
      fetch('/api/orders?status=received').then(r=>r.json()),
      fetch('/api/orders?status=ready').then(r=>r.json()),
    ]);
    allOrders = [...rec,...rdy].sort((a,b)=>new Date(b.created_at)-new Date(a.created_at));
    renderOrders();
  } catch(e) {}
}

function renderOrders() {
  const el = document.getElementById('ordersList');
  let list = currentFilter === 'all' ? allOrders : allOrders.filter(o=>o.status===currentFilter);
  el.innerHTML = list.length ? list.map(o=>orderCardHTML(o,false)).join('') :
    `<div class="empty-state"><div class="empty-state-icon">📋</div><h3>${lang==='fr'?'Aucune commande':'لا توجد طلبات'}</h3></div>`;
}

function filterOrders(f, btn) {
  currentFilter = f;
  document.querySelectorAll('.filter-tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderOrders();
}

async function searchOrders(q) {
  if (!q.trim()) { renderOrders(); return; }
  const data = await fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r=>r.json());
  document.getElementById('ordersList').innerHTML = data.filter(o=>o.status!=='completed').map(o=>orderCardHTML(o,false)).join('');
}

async function loadHistory() {
  document.getElementById('historyList').innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
  const data = await fetch('/api/orders?status=completed').then(r=>r.json());
  document.getElementById('historyList').innerHTML = data.length ? data.map(o=>orderCardHTML(o,false)).join('') :
    `<div class="empty-state"><div class="empty-state-icon">🗂️</div><h3>${lang==='fr'?'Aucune commande terminée':'لا توجد مكتملة'}</h3></div>`;
}

function orderCardHTML(o, compact) {
  const items = Array.isArray(o.items) ? o.items : [];
  const itemsCount = items.length || 1;
  const total = parseFloat(o.total_price || 0) || items.reduce((s,it)=>s+parseFloat(it.final_price||0),0) || parseFloat(o.final_price||0);
  const status = o.global_status || o.status || 'received';
  const badges = {
    received:{lbl:lang==='fr'?'Reçu':'مستلم',cls:'badge-received'},
    ready:{lbl:lang==='fr'?'Prêt':'جاهز',cls:'badge-ready'},
    completed:{lbl:lang==='fr'?'Terminé':'مكتمل',cls:'badge-completed'}
  };
  const st = badges[status] || badges.received;
  const articlesLbl = lang==='fr'
    ? `${itemsCount} article${itemsCount>1?'s':''}`
    : `${itemsCount} ${itemsCount>1?'قطع':'قطعة'}`;
  const summary = items.length > 1
    ? articlesLbl
    : (o.article_fr || (CATALOG[o.article_type]||{})[lang==='fr'?'fr':'ar'] || o.article_type || '') + ' — ' +
      (o.service_fr || SERVICES[o.service_type]?.[lang==='fr'?'fr':'ar'] || '');
  const hvTag = items.some(it=>it.is_high_value) || o.is_high_value
    ? `<span style="background:var(--accent-light);color:#92400E;padding:2px 7px;border-radius:10px;font-size:.7rem;font-weight:700;margin-left:6px">⭐ ${lang==='fr'?'Haute valeur':'قيمة عالية'}</span>` : '';
  const readyBtn = !compact && status==='received'
    ? `<button class="btn btn-success" style="padding:8px 14px;font-size:.82rem" onclick="event.stopPropagation();markReady(${o.id})">✅ ${lang==='fr'?'Tout marquer Prêt':'تعيين الكل جاهز'}</button>` : '';
  const deleteBtn = !compact ? `<button class="btn btn-danger" style="padding:8px 14px;font-size:.82rem" onclick="event.stopPropagation();deleteOrder(${o.id})">🗑️ ${lang==='fr'?'Supprimer':'حذف'}</button>` : '';

  return `<div class="order-card s-${status}" onclick="openDetail(${o.id})">
    <div class="order-main">
      <div class="order-number">${o.order_number} · ${o.pickup_code}</div>
      <div class="order-customer">${o.customer_name}${hvTag}</div>
      <div class="order-detail">${summary}${items.length>1?` · <b>${articlesLbl}</b>`:''}</div>
      <div class="order-phone">📞 ${o.customer_phone}</div>
      <div style="margin-top:7px"><span class="badge ${st.cls}">${st.lbl}</span></div>
    </div>
    <div class="order-meta">
      <div class="order-price">${total.toFixed(2)}</div>
      <div class="order-price-unit">MAD${items.length>1?' · '+lang==='fr'?'total':'مجموع':''}</div>
      <div class="order-date">📅 ${o.expected_pickup_date}</div>
    </div>
    ${!compact ? `<div class="order-actions">${readyBtn}<button class="btn btn-ghost" style="padding:8px 14px;font-size:.82rem" onclick="event.stopPropagation();openDetail(${o.id})">🔍 ${lang==='fr'?'Détails':'تفاصيل'}</button>${deleteBtn}</div>` : ''}
  </div>`;
}

async function markReady(id) {
  if (!confirm(lang==='fr'?'Marquer cette commande comme prête ?':'تعيين هذا الطلب كجاهز؟')) return;
  const r = await fetch(`/api/orders/${id}/status`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'ready'})});
  const d = await r.json();
  if (d.success) {
    showToast(lang==='fr'?'✅ Statut mis à jour !':'✅ تم التحديث !','success');
    if (d.whatsapp_msg) showWAPrompt(d.order, d.whatsapp_msg);
    loadOrders(); loadDashboard();
  }
}

function showWAPrompt(order, waMsg) {
  const phone = order.customer_phone?.replace(/\D/g,'') || '';
  const waLink = `https://wa.me/${phone.startsWith('0')?'212'+phone.slice(1):phone}?text=${encodeURIComponent(waMsg)}`;
  const html = `<div>
    <h3 style="font-weight:800;color:var(--navy);margin-bottom:12px">💬 ${lang==='fr'?'Envoyer le message au client ?':'إرسال رسالة للزبون؟'}</h3>
    <div class="whatsapp-cta">
      <div class="whatsapp-msg">${waMsg}</div>
      <div class="whatsapp-btns">
        <button class="btn btn-success" onclick="window.open('${waLink}','_blank')">📱 WhatsApp</button>
        <button class="btn btn-ghost" onclick="navigator.clipboard.writeText(${JSON.stringify(waMsg)});showToast('${lang==='fr'?'Copié !':'تم النسخ !'}','success')">📋 ${lang==='fr'?'Copier':'نسخ'}</button>
        <button class="btn btn-ghost" onclick="closeModal()">${lang==='fr'?'Ignorer':'تجاهل'}</button>
      </div>
    </div>
  </div>`;
  openModal(html);
}

/* ════ DETAIL ════ */
async function openDetail(id) {
  openModal('<div class="loading-spinner"><div class="spinner"></div></div>');
  const o = await fetch(`/api/orders/${id}`).then(r=>r.json());
  const items = Array.isArray(o.items) ? o.items : [];
  const status = o.global_status || o.status || 'received';
  const total = parseFloat(o.total_price || 0) || items.reduce((s,it)=>s+parseFloat(it.final_price||0),0);
  const statusLabel = {received:lang==='fr'?'Reçu':'مستلم',ready:lang==='fr'?'Prêt':'جاهز',completed:lang==='fr'?'Terminé':'مكتمل'};
  const badges = {received:'badge-received',ready:'badge-ready',completed:'badge-completed'};
  const hist = (o.history||[]).map(h=>`<li class="history-item"><div class="history-dot"></div><div><div style="font-weight:600;color:var(--text)">${h.action} — ${h.details||''}</div><div style="font-size:.78rem;color:var(--text-light)">${h.timestamp}</div></div></li>`).join('');

  // Liste des articles avec bouton "Marquer prêt" individuel
  const itemRows = items.map((it,i) => {
    const a = CATALOG[it.article_type]||{};
    const aL = it.article_fr || a[lang==='fr'?'fr':'ar'] || it.article_type;
    const sL = it.service_fr || SERVICES[it.service_type]?.[lang==='fr'?'fr':'ar'] || it.service_type;
    const isReady = it.status === 'ready' || it.status === 'completed';
    const cls = isReady ? 'badge-ready' : 'badge-received';
    const lbl = isReady ? (lang==='fr'?'Prêt':'جاهز') : (lang==='fr'?'Reçu':'مستلم');
    const action = (status !== 'completed' && !isReady)
      ? `<button class="btn btn-success" style="padding:6px 12px;font-size:.78rem;margin-top:6px" onclick="markItemReady(${o.id},${it.id})">✅ ${lang==='fr'?'Marquer Prêt':'تعيين جاهز'}</button>`
      : `<span style="font-size:.78rem;color:var(--success,#22c55e);font-weight:700">✅ ${lbl}</span>`;
    return `<div style="background:var(--bg);border-radius:8px;padding:10px 12px;margin-bottom:8px;border-left:3px solid var(--primary)">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px">
        <div style="flex:1;min-width:200px">
          <div style="font-weight:700;font-size:.92rem;color:var(--navy)">${i+1}. ${aL}</div>
          <div style="font-size:.82rem;color:var(--text-mid)">${sL} · <span class="badge ${cls}" style="font-size:.72rem">${lbl}</span></div>
          ${it.notes?`<div style="font-size:.78rem;color:var(--text-light);margin-top:2px">📝 ${it.notes}</div>`:''}
          ${action}
        </div>
        <div style="font-weight:800;color:var(--primary);font-size:1rem">${parseFloat(it.final_price||0).toFixed(2)} MAD</div>
      </div>
    </div>`;
  }).join('');

  const itemsBlock = items.length ? `
    <div style="margin:14px 0">
      <div style="font-weight:700;font-size:.95rem;color:var(--navy);margin-bottom:8px">
        📦 ${lang==='fr'?`Articles (${items.length})`:`القطع (${items.length})`}
      </div>
      ${itemRows}
      <div style="background:var(--navy,#0F172A);color:#fff;border-radius:8px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;margin-top:8px">
        <span style="font-weight:700;font-size:.9rem">${lang==='fr'?'TOTAL COMMANDE':'مجموع الطلب'}</span>
        <span style="font-size:1.2rem;font-weight:800">${total.toFixed(2)} MAD</span>
      </div>
      ${status==='received'?`<div style="font-size:.8rem;color:var(--text-mid);margin-top:8px;font-style:italic">ℹ️ ${lang==='fr'?'La commande passera à « Prête » quand tous les articles seront prêts.':'يُعلَّم الطلب جاهزًا عند جهوز جميع القطع.'}</div>`:''}
    </div>` : '';

  const html = `
    <div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;flex-wrap:wrap">
        <h2 style="font-weight:800;font-size:1.3rem;color:var(--navy)">${o.order_number}</h2>
        <span class="badge ${badges[status]||'badge-received'}">${statusLabel[status]||''}</span>
      </div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Client':'الزبون'}</div><div class="detail-item-value">${o.customer_name}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Téléphone':'رقم الهاتف'}</div><div class="detail-item-value">${o.customer_phone}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Code retrait':'رمز الاستلام'}</div><div class="detail-item-value" style="font-size:1.1rem;color:var(--primary);font-weight:800;letter-spacing:.12em">${o.pickup_code}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Date de dépôt':'تاريخ الاستلام'}</div><div class="detail-item-value">${o.deposit_date}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Date de retrait':'تاريخ التسليم'}</div><div class="detail-item-value">${o.expected_pickup_date}</div></div>
        ${o.authorized_person_name?`<div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Personne autorisée':'الشخص المفوّض'}</div><div class="detail-item-value">${o.authorized_person_name} (${o.authorized_person_relation||'—'})</div></div>`:''}
      </div>
      ${itemsBlock}
      ${o.article_photo?`<img src="/static/uploads/${o.article_photo}" style="max-width:100%;border-radius:var(--radius);margin:12px 0;box-shadow:var(--shadow)" alt="photo"/>`:''}
      ${o.notes?`<div style="background:var(--bg);border-radius:var(--radius-sm);padding:12px 14px;font-size:.9rem;color:var(--text-mid);margin:8px 0">${o.notes}</div>`:''}
      ${hist?`<div style="margin-top:16px"><div style="font-weight:700;font-size:.9rem;color:var(--navy);margin-bottom:8px">Historique</div><ul class="history-timeline">${hist}</ul></div>`:''}
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
        ${status==='received'?`<button class="btn btn-success" onclick="closeModal();markReady(${o.id})">✅ ${lang==='fr'?'Tout marquer Prêt':'تعيين الكل جاهز'}</button>`:''}
        <button class="btn btn-primary" onclick='showReceiptModal(${JSON.stringify(o).replace(/"/g,"&quot;").replace(/'/g,"&#39;")})'>🧾 ${lang==='fr'?'Reçu':'إيصال'}</button>
        ${status!=='completed'?`<button class="btn btn-warning" onclick="openEditModal(${o.id})">✏️ ${lang==='fr'?'Modifier':'تعديل'}</button>`:''}
        <button class="btn btn-danger" onclick="deleteOrder(${o.id})">🗑️ ${lang==='fr'?'Supprimer':'حذف'}</button>
        <button class="btn btn-ghost" onclick="closeModal()">${lang==='fr'?'Fermer':'إغلاق'}</button>
      </div>
    </div>`;
  document.getElementById('modalContent').innerHTML = html;
}

/**
 * Marque un item (article) individuel comme prêt via /api/orders/<oid>/items/<iid>/ready.
 */
async function markItemReady(orderId, itemId) {
  if (!confirm(lang==='fr'?'Marquer cet article comme prêt ?':'تعيين هذه القطعة كجاهزة؟')) return;
  try {
    const r = await fetch(`/api/orders/${orderId}/items/${itemId}/ready`, { method: 'PUT' });
    const d = await r.json();
    if (d.success) {
      showToast(lang==='fr'?'✅ Article marqué prêt !':'✅ تم !','success');
      if (d.all_ready && d.whatsapp_msg) showWAPrompt(d.order, d.whatsapp_msg);
      loadOrders();
      if (typeof loadDashboard === 'function') loadDashboard();
      openDetail(orderId);
    } else {
      showToast('Erreur: ' + (d.error || ''), 'error');
    }
  } catch(e) {
    showToast('Erreur réseau', 'error');
  }
}



/* ════ EDIT ORDER ════ */
async function openEditModal(id) {
  openModal('<div class="loading-spinner"><div class="spinner"></div></div>');
  const o = await fetch(`/api/orders/${id}`).then(r=>r.json());

  // Build article options
  let articleOpts = Object.entries(CATALOG).map(([k,v])=>
    `<option value="${k}" ${k===o.article_type?'selected':''}>${v.fr} / ${v.ar}</option>`
  ).join('');
  // Build service options
  let serviceOpts = Object.entries(SERVICES).map(([k,v])=>
    `<option value="${k}" ${k===o.service_type?'selected':''}>${v.fr} / ${v.ar}</option>`
  ).join('');

  const html = `
    <div>
      <h3 style="font-weight:800;font-size:1.2rem;color:var(--navy);margin-bottom:18px">✏️ ${lang==='fr'?'Modifier la commande':'تعديل الطلب'} — ${o.order_number}</h3>
      <div style="display:flex;flex-direction:column;gap:12px">
        <div>
          <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Nom du client':'اسم الزبون'}</label>
          <input id="edit_customer_name" class="input" value="${o.customer_name||''}" style="margin-top:4px"/>
        </div>
        <div>
          <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Téléphone':'رقم الهاتف'}</label>
          <input id="edit_customer_phone" class="input" value="${o.customer_phone||''}" style="margin-top:4px"/>
        </div>
        <div>
          <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Article':'القطعة'}</label>
          <select id="edit_article_type" class="input" style="margin-top:4px">
            <option value="">--</option>${articleOpts}
          </select>
        </div>
        <div>
          <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Service':'الخدمة'}</label>
          <select id="edit_service_type" class="input" style="margin-top:4px">
            <option value="">--</option>${serviceOpts}
          </select>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div>
            <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Date de dépôt':'تاريخ الاستلام'}</label>
            <input id="edit_deposit_date" type="date" class="input" value="${o.deposit_date||''}" style="margin-top:4px"/>
          </div>
          <div>
            <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Date de retrait':'تاريخ التسليم'}</label>
            <input id="edit_pickup_date" type="date" class="input" value="${o.expected_pickup_date||''}" style="margin-top:4px"/>
          </div>
        </div>
        <div>
          <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Prix final (MAD)':'السعر النهائي (درهم)'}</label>
          <input id="edit_final_price" type="number" step="0.01" class="input" value="${parseFloat(o.final_price||0).toFixed(2)}" style="margin-top:4px"/>
        </div>
        <div>
          <label style="font-size:.82rem;font-weight:600;color:var(--text-mid)">${lang==='fr'?'Notes':'ملاحظات'}</label>
          <textarea id="edit_notes" class="input" rows="2" style="margin-top:4px;resize:vertical">${o.notes||''}</textarea>
        </div>
        <div style="display:flex;gap:10px;margin-top:6px">
          <button class="btn btn-primary btn-full" onclick="submitEdit(${id})">💾 ${lang==='fr'?'Enregistrer':'حفظ'}</button>
          <button class="btn btn-ghost btn-full" onclick="closeModal()">${lang==='fr'?'Annuler':'إلغاء'}</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modalContent').innerHTML = html;
  // Auto-calcul du prix selon catalogue
document.getElementById('edit_article_type').addEventListener('change', updateEditPrice);
document.getElementById('edit_service_type').addEventListener('change', updateEditPrice);
}

async function submitEdit(id) {
  const fd = new FormData();
  fd.append('customer_name', document.getElementById('edit_customer_name').value);
  fd.append('customer_phone', document.getElementById('edit_customer_phone').value);
  fd.append('article_type', document.getElementById('edit_article_type').value);
  fd.append('service_type', document.getElementById('edit_service_type').value);
  fd.append('deposit_date', document.getElementById('edit_deposit_date').value);
  fd.append('expected_pickup_date', document.getElementById('edit_pickup_date').value);
  fd.append('final_price', document.getElementById('edit_final_price').value);
  fd.append('price_overridden', '1');
  fd.append('notes', document.getElementById('edit_notes').value);

  try {
    const r = await fetch(`/api/orders/${id}`, { method: 'PUT', body: fd });
    const d = await r.json();
    if (d.success) {
      showToast(lang==='fr'?'✅ Commande modifiée !':'✅ تم التعديل !', 'success');
      closeModal();
      loadOrders();
      loadDashboard();
    } else {
      showToast('Erreur: ' + (d.error||''), 'error');
    }
  } catch(e) {
    showToast('Erreur réseau', 'error');
  }
}

function updateEditPrice() {
  const article = document.getElementById('edit_article_type').value;
  const service = document.getElementById('edit_service_type').value;
  if (!article || !service) return;
  const art = CATALOG[article];
  if (!art) return;

  let priceNum = null;

  if (service === 'nettoyage_repassage') {
    const n = art.nettoyage;
    const r = art.repassage;
    if (n !== null && n !== undefined && r !== null && r !== undefined) {
      const nMin = typeof n === 'object' ? n.min : n;
      priceNum = nMin + r;
    }
  } else {
    const p = art[service];
    if (p !== null && p !== undefined) {
      priceNum = typeof p === 'object' ? p.min : p;
    }
  }

  if (priceNum !== null) {
    document.getElementById('edit_final_price').value = priceNum.toFixed(2);
  }
}

async function deleteOrder(id) {
  const msg = lang==='fr'
    ? 'Supprimer définitivement cette commande ? Cette action est irréversible.'
    : 'حذف هذا الطلب نهائياً؟ هذا الإجراء لا يمكن التراجع عنه.';
  if (!confirm(msg)) return;
  try {
    const r = await fetch(`/api/orders/${id}`, { method: 'DELETE' });
    const d = await r.json();
    if (d.success) {
      showToast(lang==='fr'?'🗑️ Commande supprimée !':'🗑️ تم الحذف !', 'success');
      closeModal();
      loadOrders();
      loadDashboard();
    } else {
      showToast('Erreur: ' + (d.error||''), 'error');
    }
  } catch(e) {
    showToast('Erreur réseau', 'error');
  }
}

/* ════ PICKUP ════ */
async function lookupPickup() {
  const code = document.getElementById('pickupCodeField').value.trim().toUpperCase();
  if (code.length < 4) { showToast(lang==='fr'?'Entrez un code valide':'أدخل رمزاً صحيحاً','warning'); return; }
  const r = await fetch(`/api/pickup/${code}`);
  const d = await r.json();
  if (!r.ok) { showToast(d.error||'Code invalide','error'); document.getElementById('pickupResult').innerHTML=''; return; }
  const art = CATALOG[d.article_type]||{};
  const artL = d.article_fr||art[lang==='fr'?'fr':'ar']||d.article_type;
  const svcL = d.service_fr||SERVICES[d.service_type]?.[lang==='fr'?'fr':'ar']||'';
  document.getElementById('pickupResult').innerHTML = `
    <div class="form-card" style="max-width:580px;border-top:4px solid var(--success)">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:18px;font-size:1.1rem;font-weight:700;color:var(--success)">✅ ${lang==='fr'?'Commande prête !':'الطلب جاهز !'}</div>
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Client':'الزبون'}</div><div class="detail-item-value">${d.customer_name}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Commande':'الطلب'}</div><div class="detail-item-value">${d.order_number}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Article':'القطعة'}</div><div class="detail-item-value">${artL}</div></div>
        <div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Prix':'السعر'}</div><div class="detail-item-value" style="font-size:1.2rem;font-weight:800;color:var(--navy)">${parseFloat(d.final_price||0).toFixed(2)} MAD</div></div>
        ${d.authorized_person_name?`<div class="detail-item"><div class="detail-item-label">${lang==='fr'?'Pers. autorisée':'المفوّض'}</div><div class="detail-item-value">${d.authorized_person_name} (${d.authorized_person_relation||''})</div></div>`:''}
      </div>
      ${d.article_photo?`<img src="/static/uploads/${d.article_photo}" style="max-width:100%;border-radius:var(--radius);margin:12px 0" alt="photo"/>`:''}
      <button class="btn btn-success btn-lg btn-full" style="margin-top:12px" onclick="confirmPickup('${code}')">
        📤 ${lang==='fr'?'Confirmer le Retrait':'تأكيد الاستلام'}
      </button>
    </div>`;
}

async function confirmPickup(code) {
  const r = await fetch(`/api/pickup/${code}/confirm`,{method:'POST'});
  const d = await r.json();
  if (d.success) {
    document.getElementById('pickupResult').innerHTML='';
    document.getElementById('pickupCodeField').value='';
    showToast(lang==='fr'?'✅ Retrait confirmé !':'✅ تم تأكيد الاستلام !','success');
    loadDashboard();
  }
}

/* ════ SETTINGS ════ */
function loadSettings() {
  // Page réglages — réservée au gérant
}

/* ════ RAPPELS AUTOMATIQUES ════ */
async function runMonthlyReminders() {
  const btn = document.getElementById('btnMonthly');
  btn.disabled = true;
  const el = document.getElementById('monthlyRemindersList');
  el.innerHTML = '<div class="loading-spinner" style="padding:16px"><div class="spinner"></div></div>';
  try {
    const data = await fetch('/api/reminders/monthly').then(r=>r.json());
    if (!data.length) {
      el.innerHTML = `<div style="padding:12px;color:var(--success);font-weight:600;font-size:.9rem">✅ ${lang==='fr'?'Aucun article en retard — tout est à jour.':'لا توجد قطع متأخرة.'}</div>`;
    } else {
      el.innerHTML = data.map(o => reminderCardHTML(o, 'monthly')).join('');
    }
  } catch(e) {
    el.innerHTML = `<div style="color:var(--danger);padding:10px">Erreur réseau</div>`;
  }
  btn.disabled = false;
}

async function runThreeMonthAlerts() {
  const btn = document.getElementById('btnThreeMonth');
  btn.disabled = true;
  const el = document.getElementById('threeMonthAlertsList');
  el.innerHTML = '<div class="loading-spinner" style="padding:16px"><div class="spinner"></div></div>';
  try {
    const data = await fetch('/api/reminders/threemonths').then(r=>r.json());
    if (!data.length) {
      el.innerHTML = `<div style="padding:12px;color:var(--success);font-weight:600;font-size:.9rem">✅ ${lang==='fr'?'Aucun article proche des 3 mois.':'لا توجد قطع تقترب من 3 أشهر.'}</div>`;
    } else {
      el.innerHTML = data.map(o => reminderCardHTML(o, 'alert')).join('');
    }
  } catch(e) {
    el.innerHTML = `<div style="color:var(--danger);padding:10px">Erreur réseau</div>`;
  }
  btn.disabled = false;
}

function reminderCardHTML(o, type) {
  const msgEsc = o.message.replace(/`/g,'\\`').replace(/\$/g,'\\$');
  const isAlert = type === 'alert';
  return `
  <div style="background:${isAlert?'#FEF2F2':'var(--white)'};border:1px solid ${isAlert?'#FECACA':'var(--border)'};border-radius:var(--radius);padding:14px 16px;margin-top:10px">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap">
      <div>
        <div style="font-weight:700;color:var(--navy);font-size:.92rem">${o.customer_name} — ${o.order_number}</div>
        <div style="font-size:.82rem;color:var(--text-mid);margin-top:2px">📞 ${o.customer_phone} &nbsp;|&nbsp; ${lang==='fr'?'Dépôt :':'الإيداع :'} ${o.deposit_date}${isAlert?` &nbsp;|&nbsp; ⚠️ Limite : ${o.deadline}`:''}</div>
        <div style="font-size:.82rem;color:var(--text-mid);margin-top:2px">👔 ${o.article_fr}</div>
      </div>
      <div style="display:flex;gap:8px;flex-shrink:0">
        <a href="${o.wa_link}" target="_blank" class="btn btn-success" style="padding:8px 14px;font-size:.82rem;text-decoration:none">📱 WA</a>
        <button class="btn btn-ghost" style="padding:8px 14px;font-size:.82rem" onclick="navigator.clipboard.writeText(\`${msgEsc}\`);showToast('${lang==='fr'?'Copié !':'تم النسخ !'}','success')">📋</button>
      </div>
    </div>
    <div style="background:white;border-radius:8px;padding:10px 12px;margin-top:10px;font-size:.82rem;color:var(--text-mid);white-space:pre-wrap;line-height:1.5;border:1px solid var(--border)">${o.message}</div>
  </div>`;
}

/* ════ MODAL ════ */
function openModal(html) {
  document.getElementById('modalContent').innerHTML = html;
  document.getElementById('modalOverlay').classList.add('show');
  document.getElementById('mainModal').classList.add('show');
  document.body.style.overflow = 'hidden';
}
function closeModal() {
  document.getElementById('modalOverlay').classList.remove('show');
  document.getElementById('mainModal').classList.remove('show');
  document.body.style.overflow = '';
}

/* ════ TOAST ════ */
function showToast(msg, type='info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(()=>t.classList.remove('show'), 4000);
}


/* ════════════ EMPLOYEES (gérant) ════════════ */
async function loadEmployees() {
  const list = document.getElementById('employeesList');
  if (!list) return;
  list.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
  try {
    const r = await fetch('/api/employees');
    if (!r.ok) {
      list.innerHTML = `<div class="empty-state"><p>${lang==='fr'?'Accès refusé':'الوصول مرفوض'}</p></div>`;
      return;
    }
    const data = await r.json();
    if (!data.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-state-icon">👥</div><p>${lang==='fr'?'Aucun employé pour l\'instant':'لا يوجد موظفون بعد'}</p></div>`;
      return;
    }
    list.innerHTML = data.map(u => `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:8px;background:var(--white)">
        <div>
          <div style="font-weight:700;color:var(--navy)">${u.full_name}</div>
          <div style="font-size:.82rem;color:var(--text-mid)">@${u.username}</div>
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn btn-ghost" style="padding:6px 10px;font-size:.78rem" onclick="resetEmployeePassword(${u.id})">🔑 ${lang==='fr'?'Mot de passe':'كلمة المرور'}</button>
          <button class="btn btn-danger" style="padding:6px 10px;font-size:.78rem" onclick="deleteEmployee(${u.id},'${(u.full_name||'').replace(/'/g,"\\'")}')">🗑️</button>
        </div>
      </div>`).join('');
  } catch(e) {
    list.innerHTML = `<div style="color:var(--danger);padding:10px">Erreur réseau</div>`;
  }
}

async function createEmployee(form) {
  const full_name = form.full_name.value.trim();
  const username  = form.username.value.trim().toLowerCase();
  const password  = form.password.value;
  if (!full_name || !username || !password) {
    showToast(lang==='fr'?'Remplissez tous les champs':'املأ كل الحقول','error');
    return;
  }
  if (password.length < 4) {
    showToast(lang==='fr'?'Mot de passe trop court (4 min)':'كلمة المرور قصيرة (4 حد أدنى)','error');
    return;
  }
  try {
    const r = await fetch('/api/employees', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({full_name, username, password})
    });
    const d = await r.json();
    if (d.success) {
      showToast(lang==='fr'?'✅ Employé créé !':'✅ تم إنشاء الحساب !','success');
      form.reset();
      loadEmployees();
    } else {
      showToast('Erreur: ' + (d.error || (lang==='fr'?'Création impossible':'فشل الإنشاء')), 'error');
    }
  } catch(e) {
    showToast('Erreur réseau', 'error');
  }
}

async function deleteEmployee(uid, name) {
  if (!confirm((lang==='fr'?'Supprimer ':'حذف ') + (name||''))) return;
  try {
    const r = await fetch(`/api/employees/${uid}`, { method: 'DELETE' });
    const d = await r.json();
    if (d.success) { showToast(lang==='fr'?'🗑️ Supprimé':'🗑️ تم','success'); loadEmployees(); }
    else showToast('Erreur: ' + (d.error||''), 'error');
  } catch(e) { showToast('Erreur réseau', 'error'); }
}

async function resetEmployeePassword(uid) {
  const pwd = prompt(lang==='fr'?'Nouveau mot de passe (4 min) :':'كلمة المرور الجديدة (4 حد أدنى):');
  if (!pwd || pwd.length < 4) return;
  try {
    const r = await fetch(`/api/employees/${uid}/password`, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({password: pwd})
    });
    const d = await r.json();
    if (d.success) showToast(lang==='fr'?'✅ Mot de passe mis à jour':'✅ تم التحديث','success');
    else showToast('Erreur: ' + (d.error||''), 'error');
  } catch(e) { showToast('Erreur réseau', 'error'); }
}

document.addEventListener('DOMContentLoaded', () => {
  const f = document.getElementById('employeeForm');
  if (f) {
    f.addEventListener('submit', e => { e.preventDefault(); createEmployee(f); });
  }
});
