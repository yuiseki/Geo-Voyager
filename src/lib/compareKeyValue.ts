/**
 * 2つのkey-valueペアのvalueを比較する
 * @param entry1 比較対象1 { key: string, value: number }
 * @param entry2 比較対象2 { key: string, value: number }
 * @returns valueの大きいentry
 */
export const compareKeyValue = (
  entry1: { key: string; value: number },
  entry2: { key: string; value: number }
) => {
  return entry1.value > entry2.value ? entry1 : entry2;
};
