import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";

import { ProductForm, ProductFormValues, initialValues, toChanges } from "../../components/ProductForm";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { vendorService } from "../../services/vendor";

export default function AddProduct() {
  useStatusBar("dark");
  const { shop } = useLocalSearchParams<{ shop: string }>();
  const queryClient = useQueryClient();

  const [values, setValues] = useState<ProductFormValues>(initialValues());
  const [errors, setErrors] = useState({});
  const [problem, setProblem] = useState<string | null>(null);

  const add = useMutation({
    mutationFn: (changes: Parameters<typeof vendorService.addProduct>[0]) =>
      vendorService.addProduct(changes),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["vendor-products"] });
      // Go to the product rather than back to the list: a photo needs a product to
      // belong to, so this is the first moment one can be added — and a product
      // with no photo rarely sells. Replace, so Back doesn't reopen a blank form.
      router.replace({ pathname: "/vendor-product/[id]", params: { id: created.id } });
    },
    onError: (e) => setProblem(errorMessage(e)),
  });

  const back = () => (router.canGoBack() ? router.back() : router.replace("/(vendor)/products"));

  const submit = () => {
    setProblem(null);
    const result = toChanges(values);
    if ("errors" in result) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    add.mutate({ ...result.changes, business: shop, name: result.changes.name! });
  };

  return (
    <ProductForm
      title="Add a product"
      values={values}
      onChange={(next) => {
        setValues(next);
        // Clear the complaint as soon as they start fixing it — leaving it on
        // screen while they retype reads as if the new value is wrong too.
        if (Object.keys(errors).length) setErrors({});
        if (problem) setProblem(null);
      }}
      onSubmit={submit}
      submitLabel="Add to my shop"
      saving={add.isPending}
      problem={problem}
      errors={errors}
      onBack={back}
    />
  );
}
