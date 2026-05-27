/**
 * 输入：
 * - 来自普通人格记录库或安全回复记录库的列表项。
 * - 当前选中记录 ID，以及用户点击记录后的选择回调。
 * - 可选的行级操作渲染函数。
 * 输出：
 * - 渲染一个可复用的历史记录表格。
 * 作用：
 * - 让普通人格记录与安全回复记录复用同一张左侧列表表格，只在文案和操作按钮上做最小差异化。
 */
import type { ReactNode } from "react";

type RecordTableItem = {
  id: number;
  user_input: string;
  created_at: string;
  selected_persona_name?: string;
  style_name?: string;
  rag_ready?: string;
};

type Props = {
  items: RecordTableItem[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  renderActions?: ((item: RecordTableItem) => ReactNode) | undefined;
};

export function RecordTable({ items, selectedId, onSelect, renderActions }: Props) {
  return (
    <div className="overflow-hidden rounded-panel border border-line bg-white/78 shadow-card">
      <table className="min-w-full border-collapse">
        <thead className="bg-paper/85 text-left text-sm text-ink/65">
          <tr>
            <th className="px-4 py-3">ID</th>
            <th className="px-4 py-3">风格</th>
            <th className="px-4 py-3">沉淀状态</th>
            <th className="px-4 py-3">来信摘要</th>
            <th className="px-4 py-3">创建时间</th>
            {renderActions ? <th className="px-4 py-3">操作</th> : null}
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
              <td className="px-4 py-4 text-sm">{item.selected_persona_name ?? item.style_name ?? "未命名"}</td>
              <td className="px-4 py-4 text-sm">
                {item.rag_ready ? (item.rag_ready === "approved" ? "已记录" : "待补批注") : "安全样本"}
              </td>
              <td className="px-4 py-4 text-sm text-ink/76">{item.user_input.slice(0, 72)}...</td>
              <td className="px-4 py-4 text-sm text-ink/60">
                {new Date(item.created_at).toLocaleString()}
              </td>
              {renderActions ? (
                <td className="px-4 py-4 text-sm">
                  <div onClick={(event) => event.stopPropagation()}>{renderActions(item)}</div>
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
