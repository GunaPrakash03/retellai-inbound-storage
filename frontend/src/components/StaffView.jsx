import { useCallback, useEffect, useState } from "react";
import { createStaff, deleteStaff, listStaff, updateStaff } from "../api";

const EMPTY = { name: "", role: "", phone: "", extension: "" };

export default function StaffView() {
  const [staff, setStaff] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(() => {
    setLoading(true);
    listStaff()
      .then((data) => {
        setStaff(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(refresh, [refresh]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      // Trim, and send null rather than "" for blank fields — otherwise
      // "no phone" is stored two different ways depending on how the row
      // was created.
      await createStaff({
        name: form.name.trim(),
        role: form.role.trim() || null,
        phone: form.phone.trim() || null,
        extension: form.extension.trim() || null,
      });
      setForm(EMPTY);
      refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(member) {
    try {
      await updateStaff(member.id, { active: !member.active });
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRemove(member) {
    if (!window.confirm(`Remove ${member.name} from the directory?`)) return;
    try {
      await deleteStaff(member.id);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="panel-view">
      <header className="panel-header">
        <h2>Staff Directory</h2>
        <p className="panel-note">
          Who the agent can transfer callers to, and who messages can be left for.
        </p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <form className="staff-form" onSubmit={handleAdd}>
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Name"
          aria-label="Name"
        />
        <input
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
          placeholder="Role (attorney, billing…)"
          aria-label="Role"
        />
        <input
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
          placeholder="Phone"
          aria-label="Phone"
        />
        <input
          value={form.extension}
          onChange={(e) => setForm({ ...form, extension: e.target.value })}
          placeholder="Ext."
          aria-label="Extension"
        />
        <button type="submit" disabled={saving || !form.name.trim()}>
          {saving ? "Adding…" : "Add"}
        </button>
      </form>

      {loading && staff.length === 0 ? (
        <div className="empty-state">Loading…</div>
      ) : staff.length === 0 ? (
        <div className="empty-state">
          No one in the directory yet. Calls can't be transferred until someone is added.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Phone</th>
                <th>Ext.</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {staff.map((m) => (
                <tr key={m.id} className={m.active ? "" : "row-muted"}>
                  <td className="caller-name">{m.name}</td>
                  <td>{m.role || "—"}</td>
                  <td className="nowrap">{m.phone || "—"}</td>
                  <td className="nowrap">{m.extension || "—"}</td>
                  <td>
                    <span className={`pill ${m.active ? "status-contacted" : "status-closed"}`}>
                      {m.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="nowrap">
                    <button className="link-button" onClick={() => toggleActive(m)}>
                      {m.active ? "Deactivate" : "Reactivate"}
                    </button>
                    <button className="link-button danger" onClick={() => handleRemove(m)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
