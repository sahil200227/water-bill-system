import { useRef, useState, type ChangeEvent } from 'react';
import { importWaterBills } from '../services/waterBillService';

interface ImportPanelProps {
  onImported?: () => void;
}

function ImportPanel({ onImported }: ImportPanelProps) {
  const [isImporting, setIsImporting] = useState(false);
  const [popupMessage, setPopupMessage] = useState('');
  const [popupType, setPopupType] = useState<'success' | 'error'>('success');
  const [selectedFileName, setSelectedFileName] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const showPopup = (message: string, type: 'success' | 'error') => {
    setPopupMessage(message);
    setPopupType(type);
    window.setTimeout(() => {
      setPopupMessage('');
    }, 2500);
  };

  const handleFileSelection = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      setSelectedFileName('');
      showPopup('No file has been selected.', 'error');
      return;
    }

    const allowedExtensions = ['.csv', '.xlsx', '.xls'];
    const fileName = file.name.toLowerCase();
    const isSupportedFile = allowedExtensions.some((extension) => fileName.endsWith(extension));

    if (!isSupportedFile) {
      setSelectedFileName('');
      showPopup('Only CSV and Excel files are supported.', 'error');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    setSelectedFileName(file.name);

    try {
      setIsImporting(true);
      await importWaterBills(file);
      showPopup('File imported successfully.', 'success');
      onImported?.();
    } catch (error) {
      console.error('Failed to import water bills', error);
      showPopup('Failed to import file.', 'error');
    } finally {
      setIsImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="import-panel" style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-start' }}>
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={isImporting}
        style={{
          backgroundColor: '#f3f4f6',
          color: '#374151',
          border: '1px solid #d1d5db',
          borderRadius: '4px',
          padding: '4px 8px',
          cursor: 'pointer',
          fontSize: '12px',
          minWidth: '90px',
        }}
      >
        Choose File
      </button>
      <div style={{ fontSize: '12px', color: '#6b7280' }}>
        {selectedFileName ? `Selected: ${selectedFileName}` : 'CSV / Excel files only'}
      </div>
      <input
        id="import-file"
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleFileSelection}
        hidden
      />
      {popupMessage && (
        <div
          style={{
            marginTop: '8px',
            padding: '8px 10px',
            borderRadius: '4px',
            color: '#fff',
            backgroundColor: popupType === 'success' ? '#16a34a' : '#dc2626',
            display: 'inline-block',
          }}
        >
          {popupMessage}
        </div>
      )}
    </div>
  );
}

export default ImportPanel;
