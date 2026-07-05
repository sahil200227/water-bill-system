import { useRef, useState } from "react";

function WaterBillForm() {
  const [customerName, setCustomerName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [serviceAddress, setServiceAddress] = useState("");
  const [billingDate, setBillingDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [previousReading, setPreviousReading] = useState("");
  const [currentReading, setCurrentReading] = useState("");
  const [waterCharge, setWaterCharge] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "error">(
    "success",
  );
  const messageTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const previousReadingValue = Number(previousReading) || 0;
  const currentReadingValue = Number(currentReading) || 0;
  const waterChargeValue = Number(waterCharge) || 0;
  const usedUnits = Math.max(currentReadingValue - previousReadingValue, 0);
  const totalAmount = usedUnits * waterChargeValue;

  const showMessage = (text: string, type: "success" | "error") => {
    if (messageTimer.current) {
      clearTimeout(messageTimer.current);
    }

    setMessage(text);
    setMessageType(type);
    messageTimer.current = setTimeout(() => {
      setMessage("");
    }, 3000);
  };

  const saveWaterBill = async () => {
    const waterBill = {
      customerName,
      accountNumber,
      serviceAddress,
      billingDate,
      dueDate,
      previousReading: Number(previousReading),
      currentReading: Number(currentReading),
      waterCharge: Number(waterCharge),
      totalAmount,
    };

    try {
      setIsSaving(true);
      setMessage("");

      const response = await fetch("http://localhost:3000/water-bill", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(waterBill),
      });

      if (!response.ok) {
        throw new Error("Failed to save water bill");
      }

      setCustomerName("");
      setAccountNumber("");
      setServiceAddress("");
      setBillingDate("");
      setDueDate("");
      setPreviousReading("");
      setCurrentReading("");
      setWaterCharge("");
      showMessage("Water Bill Saved Successfully!", "success");
    } catch {
      showMessage("Unable to save water bill. Please check backend and DB.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div>
      <h2>Add Water Bill</h2>

      <div className="form-grid">
        <div className="form-field">
          <label>Customer Name</label>
          <input
            type="text"
            placeholder="Enter Customer Name"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Account Number</label>
          <input
            type="text"
            placeholder="Enter Account Number"
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value)}
          />
        </div>

        <div className="form-field full-width">
          <label>Service Address</label>
          <input
            type="text"
            placeholder="Enter Service Address"
            value={serviceAddress}
            onChange={(e) => setServiceAddress(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Billing Date</label>
          <input
            type="date"
            value={billingDate}
            onChange={(e) => setBillingDate(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Due Date</label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Previous Reading</label>
          <input
            type="number"
            placeholder="Enter Previous Reading"
            value={previousReading}
            onChange={(e) => setPreviousReading(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Current Reading</label>
          <input
            type="number"
            placeholder="Enter Current Reading"
            value={currentReading}
            onChange={(e) => setCurrentReading(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Water Charge</label>
          <input
            type="number"
            placeholder="Enter Water Charge"
            value={waterCharge}
            onChange={(e) => setWaterCharge(e.target.value)}
          />
        </div>

        <div className="form-field">
          <label>Total Amount</label>
          <input
            type="number"
            placeholder="Auto calculated"
            value={totalAmount}
            readOnly
          />
        </div>
      </div>

      <button onClick={saveWaterBill} disabled={isSaving}>
        {isSaving ? "Saving..." : "Save Water Bill"}
      </button>

      {message && <div className={`toast ${messageType}`}>{message}</div>}
    </div>
  );
}

export default WaterBillForm;
