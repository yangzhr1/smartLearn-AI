import js from "@eslint/js";

export default [
  {
    ignores: ["dist/"],
  },
  js.configs.recommended,
  {
    languageOptions: {
      globals: {
        document: "readonly",
        window: "readonly",
        fetch: "readonly",
        FormData: "readonly",
        console: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setImmediate: "readonly",
        queueMicrotask: "readonly",
        navigator: "readonly",
        performance: "readonly",
        MutationObserver: "readonly",
        MessageChannel: "readonly",
        MSApp: "readonly",
        reportError: "readonly",
        __REACT_DEVTOOLS_GLOBAL_HOOK__: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
    },
  },
];
