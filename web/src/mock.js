// Sample data for the GitHub Pages demo build (VITE_USE_MOCK=true). Not used
// by the container build, which calls the live /api/* endpoints.
export const MOCK_STORES = [
  { name: "Airbus Finkenwerder", menu: "Casino HH-Finkenwerder" },
  { name: "Casino", menu: "Casino HH-Finkenwerder" },
  { name: "Elbblick", menu: "Elbblick HH-Finkenwerder" },
  { name: "ZAL TechCenter", menu: "ZAL TechCenter" },
];

const DISHES = [
  {
    name: "Minestrone | Italian vegetable soup",
    category: "Soup",
    price: "1.80",
    kcal: 244,
    currency: "EUR",
    price_options: [{ label: null, amount: "1.80", currency: "EUR" }],
    allergens: ["A", "C", "G"],
    tags: [{ name: "Vegetarian", image_url: "" }],
    image_url: null,
  },
  {
    name: "Potato and pepper pot | Fried Egg | Farmhouse bread",
    category: "Main",
    price: "9.25",
    kcal: 890,
    currency: "EUR",
    price_options: [
      { label: null, amount: "9.25", currency: "EUR" },
      { label: "intern", amount: "7.25", currency: "EUR" },
    ],
    allergens: ["A", "C", "E", "F"],
    tags: [{ name: "Poultry", image_url: "" }],
    image_url: null,
  },
  {
    name: "Chunky Korma | Soy | Red Curry | Ginger | Coconut Milk | Basmati rice",
    category: "Main",
    price: "8.50",
    kcal: 640,
    currency: "EUR",
    price_options: [{ label: null, amount: "8.50", currency: "EUR" }],
    allergens: ["E", "H"],
    tags: [{ name: "Vegan", image_url: "" }],
    image_url: null,
  },
];

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

export function mockMenu(storeName, week) {
  const store = MOCK_STORES.find((s) => s.name === storeName) ?? MOCK_STORES[0];
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  const days = WEEKDAYS.map((weekday, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return {
      label: `${weekday.slice(0, 3)}. ${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.`,
      weekday,
      meals: DISHES,
    };
  });
  return { store: store.name, menu: store.menu, week: `CW: ${week ?? "?"}`, days };
}
