const toNumber = (value: number | string | null | undefined): number => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
};

export const roundUpQuantity = (value: number | string | null | undefined): number => {
  const numeric = toNumber(value);
  if (numeric <= 0) return 0;
  return Math.ceil(numeric - 1e-9);
};

export const roundUpSignedQuantity = (value: number | string | null | undefined): number => {
  const numeric = toNumber(value);
  if (Math.abs(numeric) < 1e-9) return 0;
  if (numeric > 0) return Math.ceil(numeric - 1e-9);
  return -Math.ceil(Math.abs(numeric) - 1e-9);
};

export const formatQuantity = (value: number | string | null | undefined): string =>
  String(roundUpQuantity(value));

export const formatSignedQuantity = (value: number | string | null | undefined): string => {
  const numeric = roundUpSignedQuantity(value);
  return `${numeric >= 0 ? '+' : ''}${numeric}`;
};
