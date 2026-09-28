import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { PhotoPicker } from "../../components/PhotoPicker";
import { ProductForm, ProductFormValues, initialValues, toChanges } from "../../components/ProductForm";
import { Button, EmptyState } from "../../components/ui";
import { errorMessage } from "../../config/api";
import { useStatusBar } from "../../hooks/useStatusBar";
import { vendorService } from "../../services/vendor";
import { colors } from "../../theme";

export default function EditProduct() {
  useStatusBar("dark");
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [values, setValues] = useState<ProductFormValues | null>(null);
  const [errors, setErrors] = useState({});
  const [problem, setProblem] = useState<string | null>(null);

  const product = useQuery({
    queryKey: ["vendor-product", id],
    queryFn: () => vendorService.product(id),
  });

  // Fill the form once, then leave the shop's typing alone.
  useEffect(() => {
    if (product.data && !values) setValues(initialValues(product.data));
  }, [product.data, values]);

  const save = useMutation({
    mutationFn: (changes: Parameters<typeof vendorService.updateProduct>[1]) =>
      vendorService.updateProduct(id, changes),
    onSuccess: (updated) => {
      queryClient.setQueryData(["vendor-product", id], updated);
      queryClient.invalidateQueries({ queryKey: ["vendor-products"] });
      queryClient.invalidateQueries({ queryKey: ["product", id] });
      back();
    },
    onError: (e) => setProblem(errorMessage(e)),
  });

  const back = () => (router.canGoBack() ? router.back() : router.replace("/(vendor)/products"));

  if (product.isPending || !values) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.leaf} />
      </View>
    );
  }

  if (product.isError) {
    return (
      <View style={[styles.centre, { paddingHorizontal: 20, gap: 14 }]}>
        <EmptyState icon="alert-circle" title="Couldn't open this product" body={errorMessage(product.error)} />
        <Button title="Back to my products" variant="secondary" onPress={back} />
      </View>
    );
  }

  const submit = () => {
    setProblem(null);
    const result = toChanges(values);
    if ("errors" in result) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    save.mutate(result.changes);
  };

  return (
    <ProductForm
      title={product.data.name}
      values={values}
      onChange={(next) => {
        setValues(next);
        // Clear the complaint as soon as they start fixing it — leaving it on
        // screen while they retype reads as if the new value is wrong too.
        if (Object.keys(errors).length) setErrors({});
        if (problem) setProblem(null);
      }}
      onSubmit={submit}
      submitLabel="Save changes"
      saving={save.isPending}
      problem={problem}
      errors={errors}
      existing
      // Photos upload as soon as they're chosen, so they don't wait for "Save
      // changes" — and a vendor who backs out without saving keeps them.
      photos={<PhotoPicker productId={id} />}
      onBack={back}
    />
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.sand },
});
