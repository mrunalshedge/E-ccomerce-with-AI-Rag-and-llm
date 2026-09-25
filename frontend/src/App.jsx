// Phase 1 placeholder: proves the frontend can reach the API.
// The customer / seller / admin portals come in a later phase.
import { useEffect, useState } from "react";

export default function App() {
  const [health, setHealth] = useState("checking…");
  const [products, setProducts] = useState([]);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((d) => setHealth(`${d.status} (database: ${d.database})`))
      .catch(() => setHealth("backend unreachable"));
    fetch("/api/v1/products")
      .then((r) => r.json())
      .then((d) => setProducts(d.items ?? []))
      .catch(() => setProducts([]));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>ShopSense</h1>
      <p>API status: {health}</p>
      <h2>Products</h2>
      {products.length === 0 && <p>No products yet.</p>}
      <ul>
        {products.map((p) => (
          <li key={p.id}>
            <strong>{p.title}</strong>: ₹{p.price.final_price} all-inclusive (sold by {p.seller.business_name})
          </li>
        ))}
      </ul>
    </main>
  );
}
