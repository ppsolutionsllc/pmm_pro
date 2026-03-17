import React from 'react';
import Modal from './Modal';

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  confirmClass?: string;
  loading?: boolean;
}

const ConfirmModal: React.FC<Props> = ({ open, onClose, onConfirm, title, message, confirmText = 'Підтвердити', confirmClass = 'btn-primary', loading }) => (
  <Modal
    open={open}
    onClose={onClose}
    title={title}
    size="sm"
    footer={
      <>
        <button onClick={onClose} className="btn-secondary" disabled={loading}>Скасувати</button>
        <button onClick={onConfirm} className={confirmClass} disabled={loading}>
          {loading ? 'Зачекайте...' : confirmText}
        </button>
      </>
    }
  >
    <p className="text-gray-300">{message}</p>
  </Modal>
);

export default ConfirmModal;
