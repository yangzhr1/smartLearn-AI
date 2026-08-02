import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { fetch: "readonly", FormData: "readonly" },
    },
  },
  { ignores: ["dist/"] },
];
