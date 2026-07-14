const API_URL = 'http://localhost:3000/water-bill';

function getAdminKey() {
  try {
    return typeof window !== 'undefined' ? sessionStorage.getItem('adminKey') : null;
  } catch {
    return null;
  }
}

function buildHeaders(json = false) {
  const headers: Record<string, string> = {};
  if (json) headers['Content-Type'] = 'application/json';
  const key = getAdminKey();
  if (key) headers['x-admin-key'] = key;
  return headers;
}

export async function saveWaterBill(payload: Record<string, unknown>) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: buildHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to save water bill');
  }

  return response.json();
}

export async function importWaterBills(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/import`, {
    method: 'POST',
    // cannot set Content-Type for FormData; buildHeaders only adds x-admin-key when present
    headers: buildHeaders(false),
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to import water bills');
  }

  return response.json();
}

export async function getAllWaterBills(includeHidden = false) {
  const url = includeHidden ? `${API_URL}?admin=true` : API_URL;
  const response = await fetch(url, { headers: buildHeaders(false) });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to fetch water bills');
  }

  return response.json();
}

export async function updateWaterBill(id: string, payload: Record<string, unknown>) {
  const response = await fetch(`${API_URL}/${id}`, {
    method: 'PATCH',
    headers: buildHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to update water bill');
  }

  return response.json();
}

export async function recordWaterBillPayment(id: string, payload: Record<string, unknown>) {
  const response = await fetch(`${API_URL}/${id}/payments`, {
    method: 'POST',
    headers: buildHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to record payment');
  }

  return response.json();
}

export async function deleteWaterBill(id: string) {
  const response = await fetch(`${API_URL}/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(false),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to delete water bill');
  }

  return response.json();
}

export async function hardDeleteWaterBill(id: string) {
  const response = await fetch(`${API_URL}/${id}/hard`, {
    method: 'DELETE',
    headers: buildHeaders(false),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Failed to permanently delete water bill');
  }

  return response.json();
}
