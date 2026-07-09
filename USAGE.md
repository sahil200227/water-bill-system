# Water Bill App — Usage

This project contains a NestJS backend (`backend/`) and a React frontend (`frontend/`). I added a simple list UI to view, edit, and delete saved water bills and updated frontend service calls.

Quick start

1. Start backend

```bash
cd backend
npm install
npm run start:dev
```

2. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend features added

- `WaterBillList` component shows saved water bills and supports Edit/Delete.
- `waterBillService` now includes `getAllWaterBills`, `updateWaterBill`, and `deleteWaterBill`.
- Minor CSS added to `frontend/src/App.css` to style the list table.

What to expect

- Add a water bill using the form on the main page. After saving, the new record will appear in the "Saved Water Bills" table.
- Click `Edit` to change the customer name (simple prompt UI) or `Delete` to remove the record.

Notes and troubleshooting

- Backend must be running on `http://localhost:3000` (default NestJS config). If your backend runs on a different port, update `frontend/src/services/waterBillService.ts` `API_URL` constant.
- If you use MongoDB, ensure the backend can connect to your MongoDB instance (check `backend/README.md` or environment variables in the project).

Example screenshot suggestion

I couldn't capture your screen directly here. To create an example screenshot: open the frontend in the browser, take a screenshot of the page (showing the form and the "Saved Water Bills" list), and attach it to your notes. If you want, I can generate a simple mock image file with a placeholder look — tell me if you'd like that.

If you want, I can also:
- Replace the prompt-based `Edit` with an inline editable row or modal.
- Add confirmation UI instead of `confirm()` and `prompt()` calls.
- Add pagination or search to the list.

Tell me which of the above you'd like next.
