import type { RecordItem } from "../features/records/types";

type Props = {
  items: RecordItem[];
  selectedId: number | null;
  onSelect: (id: number) => void;
};

export function RecordTable({ items, selectedId, onSelect }: Props) {
  return (
    <div className="overflow-hidden rounded-panel border border-line bg-white/78 shadow-card">
      <table className="min-w-full border-collapse">
        <thead className="bg-paper/85 text-left text-sm text-ink/65">
          <tr>
            <th className="px-4 py-3">ID</th>
            <th className="px-4 py-3">咨询师</th>
            <th className="px-4 py-3">风格</th>
            <th className="px-4 py-3">沉淀状态</th>
            <th className="px-4 py-3">来信摘要</th>
            <th className="px-4 py-3">创建时间</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className={`cursor-pointer border-t border-line ${selectedId === item.id ? "bg-peach/20" : "hover:bg-paper/60"}`}
              onClick={() => onSelect(item.id)}
            >
              <td className="px-4 py-4 text-sm">{item.id}</td>
              <td className="px-4 py-4 text-sm text-ink/70">{item.counselor_id}</td>
              <td className="px-4 py-4 text-sm">{item.selected_persona_name}</td>
              <td className="px-4 py-4 text-sm">
                {item.rag_ready === "approved" ? "已记录" : "待补批注"}
              </td>
              <td className="px-4 py-4 text-sm text-ink/76">{item.user_input.slice(0, 72)}...</td>
              <td className="px-4 py-4 text-sm text-ink/60">
                {new Date(item.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
