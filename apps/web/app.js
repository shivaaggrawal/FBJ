const state = { account: null, bounties: [], selected: null, selectedChain: null, config: null, countdownTimer: null, filters: { search: "", status: "all" } };
function apiErrorMessage(detail, fallback) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (!item || typeof item !== "object") return String(item);
      const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
      return field ? `${field}: ${item.msg || "Invalid value"}` : item.msg || "Invalid request";
    }).join("; ");
  }
  return fallback;
}
const api = (path, options = {}) => fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options })
  .then(async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(apiErrorMessage(body.detail, `Request failed (${response.status})`));
    return body;
  });

const $ = (selector) => document.querySelector(selector);
const short = (value, length = 10) => !value ? "-" : value.length > length ? `${value.slice(0, length)}...` : value;
const asDate = (value) => value ? new Date(Number(value) * 1000).toLocaleString() : "-";
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
const safeHref = (value) => /^https?:\/\//i.test(String(value || "")) ? escapeHtml(value) : "#";

function notice(message, isError = false) {
  const target = $("#notice");
  target.textContent = message;
  target.className = `notice show${isError ? " error" : ""}`;
  window.setTimeout(() => { target.className = "notice"; target.textContent = ""; }, 6000);
}

function newBountyId() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return `0x${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function connectWallet() {
  if (!window.ethereum) throw new Error("No browser wallet found. Install MetaMask or another EIP-1193 wallet.");
  if (!state.config) await loadClientConfig();
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  state.account = accounts[0];
  $("#connect-wallet").textContent = short(state.account, 12);
  await ensureExpectedChain();
}

async function ensureExpectedChain() {
  if (!window.ethereum) throw new Error("No browser wallet found. Install MetaMask or another EIP-1193 wallet.");
  if (!state.config) await loadClientConfig();
  const chainId = await window.ethereum.request({ method: "eth_chainId" });
  const expectedChain = state.config.chain_hex;
  $("#network-status").textContent = chainId === expectedChain ? state.config.chain_name : `Wrong network: ${chainId}`;
  if (chainId === expectedChain) return;
  try {
    await window.ethereum.request({ method: "wallet_switchEthereumChain", params: [{ chainId: expectedChain }] });
  } catch (error) {
    throw new Error(`Switch the wallet network to ${state.config.chain_name} before sending a transaction.`);
  }
  const switchedChain = await window.ethereum.request({ method: "eth_chainId" });
  $("#network-status").textContent = switchedChain === expectedChain ? state.config.chain_name : `Wrong network: ${switchedChain}`;
  if (switchedChain !== expectedChain) throw new Error(`Switch the wallet network to ${state.config.chain_name} before sending a transaction.`);
}

async function sendWalletTransaction(transaction) {
  if (!state.account) await connectWallet();
  await ensureExpectedChain();
  if (transaction.to === "fixture") throw new Error("Fixture mode cannot send wallet transactions. Deploy the Amoy contracts first.");
  const quotedGasPrice = BigInt(await window.ethereum.request({ method: "eth_gasPrice" }));
  const minimumAmoyGasPrice = 75_000_000_000n;
  // Use a legacy gas price with headroom. The configured Amoy RPC rejects
  // MetaMask's EIP-1559 priority-fee proposal even when the transaction is valid.
  const gasPrice = quotedGasPrice * 12n / 10n > minimumAmoyGasPrice
    ? quotedGasPrice * 12n / 10n
    : minimumAmoyGasPrice;
  return window.ethereum.request({ method: "eth_sendTransaction", params: [{
    from: state.account,
    to: transaction.to,
    data: transaction.data,
    value: transaction.value || "0x0",
    gasPrice: `0x${gasPrice.toString(16)}`,
  }] });
}

async function waitForReceipt(transactionHash) {
  for (let attempt = 0; attempt < 90; attempt += 1) {
    const receipt = await window.ethereum.request({ method: "eth_getTransactionReceipt", params: [transactionHash] });
    if (receipt) {
      if (receipt.status === "0x0") throw new Error("Wallet transaction reverted.");
      return receipt;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 2000));
  }
  throw new Error("Transaction confirmation timed out.");
}

function statusClass(status) {
  return status ? status.replaceAll("_", " ") : "unknown";
}

function validateBountyPayload(payload) {
  const address = /^0x[0-9a-fA-F]{40}$/;
  const bountyId = /^0x[0-9a-fA-F]{64}$/;
  if (!bountyId.test(payload.contract_bounty_id)) throw new Error("Could not create a valid bounty ID. Please try again.");
  if (!/^[^/\s]+\/[^/\s]+$/.test(payload.repository || "")) throw new Error("Repository must look like owner/repository.");
  if (!/^https?:\/\/github\.com\/[^/]+\/[^/]+\/issues\/\d+/i.test(payload.issue_url || "")) throw new Error("Issue URL must be a valid GitHub issue URL.");
  if (!address.test(payload.reward_token || "")) throw new Error("Token address must be a valid 42-character wallet address.");
  if (!address.test(payload.maintainer_wallet || "")) throw new Error("Connected maintainer wallet is invalid. Reconnect your wallet.");
  if (!address.test(payload.recipient_wallet || "")) throw new Error("Recipient wallet must be a valid 42-character wallet address.");
  if (!/^[1-9][0-9]*$/.test(payload.reward_amount || "")) throw new Error("Reward amount must be a positive whole number without commas.");
  if (!Number.isInteger(Number(payload.expires_at)) || Number(payload.expires_at) <= Math.floor(Date.now() / 1000)) throw new Error("Expiry must be a future date and time.");
}

function normalizedStatus(value) { return String(value || "").toLowerCase(); }

function setTransactionState(kind, title, message) {
  const panel = $("#detail-state");
  if (!panel) return;
  panel.className = `state-banner ${kind || ""}`;
  $("#state-title").textContent = title;
  $("#state-message").textContent = message;
}

function setActionAvailability() {
  if (!state.selected) return;
  const status = normalizedStatus(state.selected.status);
  const chain = state.selectedChain || {};
  const disputeOpen = Boolean(chain.dispute?.open) || ["challenged", "disputed"].includes(status);
  const settled = ["paid_out", "released", "resolved_release", "refunded", "cancelled"].includes(status);
  const challengeEnds = Number(chain.verdict?.challenge_ends_at || chain.bounty?.release_at || 0);
  const challengeOver = challengeEnds > 0 && Date.now() / 1000 >= challengeEnds;
  const isParticipant = state.account && [state.selected.maintainer_wallet, state.selected.recipient_wallet].some((wallet) => normalizedStatus(wallet) === normalizedStatus(state.account));
  $("#release-bounty").disabled = settled || disputeOpen || !challengeOver;
  $("#cancel-bounty").disabled = settled || disputeOpen || !["open"].includes(status);
  $("#refund-bounty").disabled = settled || disputeOpen || !["open", "expired"].includes(status) || (state.selected.expires_at && Date.now() / 1000 < Number(state.selected.expires_at));
  $("#open-dispute-form button").disabled = settled || disputeOpen || !isParticipant;
  document.querySelectorAll("[data-resolution]").forEach((button) => { button.disabled = !disputeOpen || settled; });
}

function renderChallengeWindow() {
  const panel = $("#challenge-panel");
  if (!panel || !state.selected) return;
  const status = normalizedStatus(state.selected.status);
  const chain = state.selectedChain || {};
  const deadline = Number(chain.verdict?.challenge_ends_at || chain.bounty?.release_at || (status === "open" ? state.selected.expires_at : 0) || 0);
  const countdown = $("#challenge-countdown");
  const message = $("#challenge-message");
  const title = $("#challenge-title");
  if (["paid_out", "released", "resolved_release", "refunded", "cancelled"].includes(status)) { title.textContent = "Settlement complete"; message.textContent = "This bounty is closed and no further actions are available."; countdown.textContent = "CLOSED"; panel.classList.add("expired"); setActionAvailability(); return; }
  const update = () => {
    const remaining = deadline - Date.now() / 1000;
    if (!deadline) { title.textContent = "Challenge window unavailable"; message.textContent = "Chain deadline will appear after a verdict is submitted."; countdown.textContent = "--:--:--"; panel.classList.remove("expired"); return; }
    if (remaining <= 0) { title.textContent = "Challenge window closed"; message.textContent = "No open dispute detected. Release is available if the bounty is otherwise eligible."; countdown.textContent = "READY"; panel.classList.add("expired"); }
    else { const days = Math.floor(remaining / 86400); const hours = Math.floor(remaining % 86400 / 3600); const minutes = Math.floor(remaining % 3600 / 60); const seconds = Math.floor(remaining % 60); title.textContent = status === "open" ? "Bounty expiry" : "Challenge window closes"; message.textContent = `Until ${new Date(deadline * 1000).toLocaleString()}`; countdown.textContent = `${days ? `${days}d ` : ""}${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`; panel.classList.remove("expired"); }
    setActionAvailability();
  };
  window.clearInterval(state.countdownTimer); update(); state.countdownTimer = window.setInterval(update, 1000);
}

function renderMetrics() {
  const counts = state.bounties.reduce((result, bounty) => {
    const status = String(bounty.status || "").toLowerCase();
    result.total += 1;
    if (["open", "under_review", "analyzing", "challenge_open"].includes(status)) result.active += 1;
    if (["paid_out", "released", "resolved_release"].includes(status)) result.paid += 1;
    if (["challenged", "disputed", "flagged_for_review", "flagged"].includes(status)) result.attention += 1;
    return result;
  }, { total: 0, active: 0, paid: 0, attention: 0 });
  $("#metric-total").textContent = counts.total;
  $("#metric-active").textContent = counts.active;
  $("#metric-paid").textContent = counts.paid;
  $("#metric-attention").textContent = counts.attention;
}

function visibleBounties() {
  const search = state.filters.search.toLowerCase();
  return state.bounties.filter((bounty) => {
    const matchesSearch = !search || `${bounty.repository} ${bounty.contract_bounty_id}`.toLowerCase().includes(search);
    const matchesStatus = state.filters.status === "all" || bounty.status === state.filters.status;
    return matchesSearch && matchesStatus;
  });
}

function renderBountyList() {
  const target = $("#bounty-list");
  const bounties = visibleBounties();
  if (!bounties.length) { target.innerHTML = '<p class="empty">No bounties match this view.</p>'; return; }
  target.innerHTML = bounties.map((bounty) => `<button class="bounty-row ${state.selected?.contract_bounty_id === bounty.contract_bounty_id ? "selected" : ""}" data-bounty="${escapeHtml(bounty.contract_bounty_id)}" type="button">
    <strong>${escapeHtml(bounty.repository)}</strong><span>${escapeHtml(short(bounty.contract_bounty_id, 18))}</span><span class="row-foot"><i>${escapeHtml(statusClass(bounty.status))}</i><i>${escapeHtml(short(bounty.reward_amount))} units</i></span>
  </button>`).join("");
  target.querySelectorAll("[data-bounty]").forEach((button) => button.addEventListener("click", () => selectBounty(button.dataset.bounty)));
}

async function loadClientConfig() {
  state.config = await api("/api/client-config");
  $("#network-status").textContent = state.config.fixture_mode ? "Fixture mode" : state.config.chain_name;
  const rewardInput = $("[name=reward_token]");
  if (rewardInput && state.config.reward_token_address) rewardInput.value = state.config.reward_token_address;
}

async function loadBounties() {
  state.bounties = await api("/api/bounties");
  $("#bounty-count").textContent = String(state.bounties.length);
  renderMetrics();
  renderBountyList();
}

function renderReview(review) {
  if (!review) return '<p class="empty">No completed review attached to this bounty yet.</p>';
  const agents = (review.agent_results || []).map((agent) => `<div class="agent-row"><span>${agent.agent}</span><span class="bar"><i style="width:${agent.score_bps / 100}%"></i></span><b>${agent.score_bps / 100}%</b></div>`).join("");
  const cid = review.evidence_cid ? `<a href="https://gateway.pinata.cloud/ipfs/${review.evidence_cid}" target="_blank" rel="noreferrer">${short(review.evidence_cid, 22)}</a>` : "-";
  const tx = review.attestation_tx_hash && state.config?.explorer_base_url ? `<a href="${state.config.explorer_base_url}/tx/${review.attestation_tx_hash}" target="_blank" rel="noreferrer">${short(review.attestation_tx_hash, 18)}</a>` : short(review.attestation_tx_hash, 18);
  return `<div class="review-score">${review.final_score_bps ? `${review.final_score_bps / 100}%` : "-"}</div>${agents}<div class="facts"><div class="fact"><b>Evidence CID</b>${cid}</div><div class="fact"><b>Evidence hash</b>${escapeHtml(short(review.evidence_hash, 22))}</div><div class="fact"><b>Attestation</b>${escapeHtml(review.attestation_status || "-")}</div><div class="fact"><b>Commit</b>${escapeHtml(short(review.commit_sha, 18))}</div><div class="fact"><b>Transaction</b>${tx}</div></div>`;
}

async function selectBounty(id) {
  state.selected = state.bounties.find((bounty) => bounty.contract_bounty_id === id);
  if (!state.selected) return;
  state.selectedChain = null;
  $("#bounty-detail").classList.remove("hidden");
  $("#detail-title").textContent = short(id, 22);
  $("#detail-repository").textContent = state.selected.repository;
  const issueLink = $("#detail-issue");
  issueLink.href = safeHref(state.selected.issue_url);
  issueLink.classList.toggle("disabled-link", issueLink.href === "#");
  $("#detail-status").textContent = statusClass(state.selected.status);
  const initialStatus = normalizedStatus(state.selected.status);
  setTransactionState(["challenged", "disputed"].includes(initialStatus) ? "disputed" : ["paid_out", "released", "resolved_release", "refunded", "cancelled"].includes(initialStatus) ? "settled" : "confirmed", initialStatus === "open" ? "Awaiting contribution" : statusClass(state.selected.status), initialStatus === "open" ? "Bounty is funded and ready for work." : "Loading the latest chain and review state...");
  $("#detail-facts").innerHTML = `<div class="fact"><b>Reward</b>${escapeHtml(state.selected.reward_amount)}</div><div class="fact"><b>Expiry</b>${escapeHtml(asDate(state.selected.expires_at))}</div><div class="fact"><b>Maintainer</b>${escapeHtml(short(state.selected.maintainer_wallet, 18))}</div><div class="fact"><b>Recipient</b>${escapeHtml(short(state.selected.recipient_wallet, 18))}</div>`;
  setActionAvailability();
  $("#review-detail").innerHTML = '<p class="empty">Loading chain state...</p>';
  await loadBounties();
  try {
    const stateResponse = await api(`/api/bounties/${id}/chain-state`);
    state.selectedChain = stateResponse;
    let review = null;
    if (state.selected.verdict_review_id) review = await api(`/api/reviews/${state.selected.verdict_review_id}`);
    $("#review-detail").innerHTML = `${renderReview(review)}<div class="facts"><div class="fact"><b>Chain bounty</b>${JSON.stringify(stateResponse.bounty).slice(0, 90)}</div><div class="fact"><b>Chain verdict</b>${stateResponse.verdict.exists ? "submitted" : "not submitted"}</div><div class="fact"><b>Dispute state</b>${stateResponse.dispute.open ? "open" : "none"}</div></div>`;
    const isDisputed = Boolean(stateResponse.dispute.open) || ["challenged", "disputed"].includes(initialStatus);
    const isSettled = ["paid_out", "released", "resolved_release", "refunded", "cancelled"].includes(initialStatus);
    setTransactionState(isDisputed ? "disputed" : isSettled ? "settled" : "confirmed", isDisputed ? "Dispute open" : isSettled ? "Settlement confirmed" : "Chain state verified", isDisputed ? "Resolver action is required before funds can move." : isSettled ? "This bounty has reached a final state." : "Review, evidence, and permitted actions are shown below.");
    renderChallengeWindow();
    setActionAvailability();
  } catch (error) {
    setTransactionState("failed", "Unable to verify chain state", error.message);
    renderChallengeWindow();
    setActionAvailability();
    $("#review-detail").innerHTML = `<p class="empty">${error.message}</p>`;
  }
}

async function createBounty(event) {
  event.preventDefault();
  // Event.currentTarget is only set while the submit listener is running.
  // Keep the form before awaiting the wallet connection.
  const formElement = event.currentTarget;
  try {
    await connectWallet();
    const form = new FormData(formElement);
    const payload = Object.fromEntries(form.entries());
    payload.contract_bounty_id = newBountyId();
    payload.maintainer_wallet = state.account;
    payload.reward_amount = String(payload.reward_amount || "").replace(/[,_\s]/g, "");
    payload.expires_at = Math.floor(new Date(payload.expires_at).getTime() / 1000);
    validateBountyPayload(payload);
    const prepared = await api("/api/bounties/prepare", { method: "POST", body: JSON.stringify(payload) });
    notice("Confirm ERC-20 approval in your wallet.");
    await waitForReceipt(await sendWalletTransaction(prepared.transaction.approval));
    notice("Confirm bounty creation in your wallet.");
    const creationTx = await sendWalletTransaction(prepared.transaction.create);
    await waitForReceipt(creationTx);
    payload.creation_tx_hash = creationTx;
    const message = await api("/api/bounties/registration-message", { method: "POST", body: JSON.stringify(payload) });
    payload.registration_signature = await window.ethereum.request({ method: "personal_sign", params: [message.message, state.account] });
    await api("/api/bounties", { method: "POST", body: JSON.stringify(payload) });
    notice("Bounty confirmed and registered.");
    formElement.reset();
    await loadBounties();
  } catch (error) { notice(error.message, true); }
}

async function prepareAndSend(path, body, confirmationPath = null, confirmationBody = {}) {
  if (!state.selected) throw new Error("Select a bounty first.");
  setTransactionState("pending", "Preparing transaction", "Waiting for the wallet to prepare this action...");
  try {
  const prepared = await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
  const hash = await sendWalletTransaction(prepared.transaction);
  setTransactionState("pending", "Transaction pending", `Waiting for confirmation: ${short(hash, 18)}`);
  notice(`Wallet transaction submitted: ${short(hash, 18)}. Waiting for confirmation...`);
  await waitForReceipt(hash);
  if (confirmationPath) {
    const confirmed = await api(confirmationPath, { method: "POST", body: JSON.stringify({ ...confirmationBody, transaction_hash: hash }) });
    if (confirmed.status === "failed") throw new Error(confirmed.error || "Wallet transaction reverted.");
    setTransactionState("confirmed", "Transaction confirmed", `Action confirmed on-chain: ${short(hash, 18)}`);
    notice(`Transaction ${confirmed.status}: ${short(hash, 18)}`);
    await loadBounties();
    return confirmed;
  }
  setTransactionState("confirmed", "Transaction confirmed", `Action confirmed on-chain: ${short(hash, 18)}`);
  notice(`Transaction confirmed: ${short(hash, 18)}`);
  return { transaction_hash: hash, status: "confirmed" };
  } catch (error) {
    setTransactionState("failed", "Transaction failed", error.message);
    throw error;
  }
}

async function loadDisputes() {
  const disputes = await api("/api/disputes");
  $("#dispute-list").innerHTML = disputes.length ? disputes.map((dispute) => `<article class="dispute-item"><div><strong>${short(dispute.bounty_id, 20)}</strong><p>${dispute.evidence_cid || "Evidence pending"}</p></div><span class="status-pill">${statusClass(dispute.status)}</span></article>`).join("") : '<p class="empty">No dispute evidence has been prepared.</p>';
}

function setView(name) {
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `${name}-view`));
  document.querySelectorAll(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === name));
  if (name === "disputes") loadDisputes().catch((error) => notice(error.message, true));
}

$("#connect-wallet").addEventListener("click", () => connectWallet().catch((error) => notice(error.message, true)));
$("#refresh-bounties").addEventListener("click", () => loadBounties().catch((error) => notice(error.message, true)));
$("#refresh-disputes").addEventListener("click", () => loadDisputes().catch((error) => notice(error.message, true)));
$("#bounty-search").addEventListener("input", (event) => { state.filters.search = event.target.value; renderBountyList(); });
$("#bounty-status").addEventListener("change", (event) => { state.filters.status = event.target.value; renderBountyList(); });
$("#create-bounty-form").addEventListener("submit", createBounty);
$("#release-bounty").addEventListener("click", async () => { try { if (!state.selected) throw new Error("Select a bounty first."); setTransactionState("pending", "Release pending", "Submitting the payout transaction..."); const result = await api(`/api/bounties/${state.selected.contract_bounty_id}/release`, { method: "POST" }); setTransactionState(result.status === "failed" ? "failed" : "confirmed", result.status === "failed" ? "Release failed" : "Release confirmed", result.error || `Payout transaction: ${short(result.transaction_hash, 18)}`); notice(`Release submitted: ${short(result.transaction_hash, 18)}`); await loadBounties(); } catch (error) { setTransactionState("failed", "Release failed", error.message); notice(error.message, true); } });
$("#cancel-bounty").addEventListener("click", () => prepareAndSend(`/api/bounties/${state.selected.contract_bounty_id}/cancel/prepare`, null, `/api/bounties/${state.selected.contract_bounty_id}/cancel/confirm`).catch((error) => notice(error.message, true)));
$("#refund-bounty").addEventListener("click", () => prepareAndSend(`/api/bounties/${state.selected.contract_bounty_id}/refund/prepare`, null, `/api/bounties/${state.selected.contract_bounty_id}/refund/confirm`).catch((error) => notice(error.message, true)));
$("#open-dispute-form").addEventListener("submit", async (event) => { event.preventDefault(); const formElement = event.currentTarget; try { const evidence = JSON.parse(new FormData(formElement).get("evidence")); await prepareAndSend(`/api/bounties/${state.selected.contract_bounty_id}/disputes/prepare`, { evidence }, `/api/bounties/${state.selected.contract_bounty_id}/disputes/confirm`); await loadDisputes(); } catch (error) { notice(error.message, true); } });
document.querySelectorAll("[data-resolution]").forEach((button) => button.addEventListener("click", () => { const resolution = Number(button.dataset.resolution); return prepareAndSend(`/api/bounties/${state.selected.contract_bounty_id}/disputes/resolve/prepare`, { resolution }, `/api/bounties/${state.selected.contract_bounty_id}/disputes/resolve/confirm`, { resolution }).catch((error) => notice(error.message, true)); }));
document.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", () => setView(link.dataset.view)));
if (window.ethereum) {
  window.ethereum.on?.("chainChanged", () => connectWallet().catch((error) => notice(error.message, true)));
  window.ethereum.on?.("accountsChanged", () => connectWallet().catch((error) => notice(error.message, true)));
}

const expiry = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); expiry.setMinutes(expiry.getMinutes() - expiry.getTimezoneOffset());
$("[name=expires_at]").value = expiry.toISOString().slice(0, 16);
loadClientConfig().then(loadBounties).catch((error) => notice(error.message, true));
