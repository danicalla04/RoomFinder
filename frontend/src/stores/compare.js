import { defineStore } from "pinia";
import { ref } from "vue";
export const useCompare = defineStore("compare", () => {
  let saved = [];
  try {
    saved = JSON.parse(localStorage.getItem("rf_compare") || "[]");
  } catch {}
  const ids = ref(saved);
  function toggle(id) {
    if (ids.value.includes(id)) ids.value = ids.value.filter((x) => x !== id);
    else if (ids.value.length < 3) ids.value.push(id);
    localStorage.setItem("rf_compare", JSON.stringify(ids.value));
  }
  return { ids, toggle };
});
