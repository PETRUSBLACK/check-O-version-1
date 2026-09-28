import { Feather } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { errorMessage } from "../config/api";
import { PickedPhoto, ProductPhoto, photosService } from "../services/photos";
import { colors, fonts } from "../theme";
import { Banner } from "./ui";

/**
 * Photos for one product: add from the camera or the gallery, choose the cover,
 * remove one.
 *
 * A note on size. Photos are taken at `quality: 0.55` and cropped square rather
 * than resized with a second library. Square is the right shape for the product
 * grid anyway, and the crop plus compression keeps a phone photo to a few hundred
 * kilobytes — which matters when a vendor is listing twenty items on metered data.
 * If real photos still come out too heavy, expo-image-manipulator is the next step.
 */
export function PhotoPicker({ productId }: { productId: string }) {
  const queryClient = useQueryClient();
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [acting, setActing] = useState<string | null>(null);

  const photos = useQuery({
    queryKey: ["product-photos", productId],
    queryFn: () => photosService.forProduct(productId),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["product-photos", productId] });
    // The shopper-facing screens read cover_image off the product itself.
    queryClient.invalidateQueries({ queryKey: ["vendor-products"] });
    queryClient.invalidateQueries({ queryKey: ["product", productId] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
  };

  const upload = useMutation({
    mutationFn: (picked: PickedPhoto) => photosService.upload(productId, picked),
    onSuccess: () => {
      refresh();
      setProblem(null);
    },
    onError: (e) => setProblem(errorMessage(e)),
  });

  const setCover = useMutation({
    mutationFn: (id: string) => photosService.makeCover(id),
    onSuccess: refresh,
    onError: (e) => setProblem(errorMessage(e)),
    onSettled: () => setActing(null),
  });

  const remove = useMutation({
    mutationFn: (id: string) => photosService.remove(id),
    onSuccess: refresh,
    onError: (e) => setProblem(errorMessage(e)),
    onSettled: () => setActing(null),
  });

  const take = async (from: "camera" | "gallery") => {
    setChoosing(false);
    setProblem(null);
    setBusy(true);
    try {
      const permission =
        from === "camera"
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permission.granted) {
        setProblem(
          from === "camera"
            ? "Check-O needs permission to use your camera. You can turn it on in your phone's settings."
            : "Check-O needs permission to open your photos. You can turn it on in your phone's settings.",
        );
        return;
      }

      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: "images",
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.55,
      };
      const result =
        from === "camera"
          ? await ImagePicker.launchCameraAsync(options)
          : await ImagePicker.launchImageLibraryAsync(options);

      if (result.canceled || !result.assets?.length) return;

      const asset = result.assets[0];
      upload.mutate({
        uri: asset.uri,
        mimeType: asset.mimeType,
        fileName: asset.fileName ?? undefined,
        fileSize: asset.fileSize,
      });
    } catch (e) {
      setProblem(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const list = photos.data ?? [];
  const working = busy || upload.isPending;

  return (
    <View style={{ gap: 10 }}>
      <View style={styles.head}>
        <Text style={styles.title}>Photos</Text>
        <Text style={styles.hint}>
          {list.length === 0
            ? "A product with no photo rarely sells."
            : "The first one is what shoppers see."}
        </Text>
      </View>

      {photos.isPending ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.leaf} />
        </View>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.strip}>
          {list.map((photo) => (
            <Thumb
              key={photo.id}
              photo={photo}
              busy={acting === photo.id}
              onMakeCover={() => {
                setActing(photo.id);
                setCover.mutate(photo.id);
              }}
              onRemove={() => {
                setActing(photo.id);
                remove.mutate(photo.id);
              }}
            />
          ))}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Add a photo"
            onPress={() => setChoosing((c) => !c)}
            disabled={working}
            style={({ pressed }) => [styles.add, pressed && { opacity: 0.7 }]}
          >
            {working ? (
              <ActivityIndicator color={colors.leaf} />
            ) : (
              <>
                <Feather name="camera" size={22} color={colors.leaf} />
                <Text style={styles.addText}>Add photo</Text>
              </>
            )}
          </Pressable>
        </ScrollView>
      )}

      {choosing ? (
        <View style={styles.choices}>
          <Choice icon="camera" label="Take a photo" onPress={() => take("camera")} />
          <Choice icon="image" label="Choose from gallery" onPress={() => take("gallery")} />
        </View>
      ) : null}

      {problem ? (
        <Banner tone="danger" icon="alert-circle">
          {problem}
        </Banner>
      ) : null}
    </View>
  );
}

function Thumb({
  photo,
  busy,
  onMakeCover,
  onRemove,
}: {
  photo: ProductPhoto;
  busy: boolean;
  onMakeCover: () => void;
  onRemove: () => void;
}) {
  // Confirming in the app rather than with Alert.alert: an OS dialog looks foreign
  // here, and Alert does nothing at all on web, which made testing lie to us once.
  const [confirming, setConfirming] = useState(false);

  return (
    <View style={styles.thumbWrap}>
      <Image source={{ uri: photo.image }} style={styles.thumb} resizeMode="cover" />

      {photo.is_cover ? (
        <View style={styles.coverBadge}>
          <Feather name="star" size={10} color={colors.white} />
          <Text style={styles.coverBadgeText}>Cover</Text>
        </View>
      ) : null}

      {busy ? (
        <View style={styles.thumbOverlay}>
          <ActivityIndicator color={colors.white} />
        </View>
      ) : confirming ? (
        <View style={styles.thumbOverlay}>
          <Text style={styles.confirmText}>Remove?</Text>
          <View style={{ flexDirection: "row", gap: 6 }}>
            <Pressable onPress={onRemove} style={[styles.miniBtn, styles.miniDanger]}>
              <Text style={styles.miniDangerText}>Yes</Text>
            </Pressable>
            <Pressable onPress={() => setConfirming(false)} style={styles.miniBtn}>
              <Text style={styles.miniText}>No</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <View style={styles.thumbActions}>
          {photo.is_cover ? null : (
            <Pressable
              accessibilityLabel="Make this the cover photo"
              onPress={onMakeCover}
              style={styles.iconBtn}
            >
              <Feather name="star" size={13} color={colors.white} />
            </Pressable>
          )}
          <Pressable
            accessibilityLabel="Remove this photo"
            onPress={() => setConfirming(true)}
            style={styles.iconBtn}
          >
            <Feather name="trash-2" size={13} color={colors.white} />
          </Pressable>
        </View>
      )}
    </View>
  );
}

function Choice({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Feather.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.choice, pressed && { opacity: 0.75 }]}
    >
      <Feather name={icon} size={16} color={colors.leaf} />
      <Text style={styles.choiceText}>{label}</Text>
    </Pressable>
  );
}

const SIZE = 92;

const styles = StyleSheet.create({
  head: { gap: 2 },
  title: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  hint: { fontFamily: fonts.body, fontSize: 12.5, lineHeight: 18, color: colors.muted },
  loading: { height: SIZE, alignItems: "center", justifyContent: "center" },
  strip: { gap: 10, paddingVertical: 2 },
  thumbWrap: {
    width: SIZE,
    height: SIZE,
    borderRadius: 14,
    overflow: "hidden",
    backgroundColor: colors.mint,
    borderWidth: 1,
    borderColor: colors.line,
  },
  thumb: { width: "100%", height: "100%" },
  coverBadge: {
    position: "absolute",
    left: 5,
    bottom: 5,
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    backgroundColor: colors.leaf,
  },
  coverBadgeText: { fontFamily: fonts.bodyBold, fontSize: 9.5, color: colors.white },
  thumbActions: { position: "absolute", top: 5, right: 5, flexDirection: "row", gap: 5 },
  iconBtn: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(11,61,46,0.72)",
  },
  thumbOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "rgba(11,61,46,0.82)",
  },
  confirmText: { fontFamily: fonts.bodyBold, fontSize: 12, color: colors.white },
  miniBtn: {
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.22)",
  },
  miniText: { fontFamily: fonts.bodyBold, fontSize: 11, color: colors.white },
  miniDanger: { backgroundColor: colors.white },
  miniDangerText: { fontFamily: fonts.bodyBold, fontSize: 11, color: "#A8321E" },
  add: {
    width: SIZE,
    height: SIZE,
    borderRadius: 14,
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: colors.line,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
  },
  addText: { fontFamily: fonts.bodySemibold, fontSize: 11.5, color: colors.leaf },
  choices: { gap: 8 },
  choice: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    paddingVertical: 11,
    paddingHorizontal: 13,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.white,
  },
  choiceText: { fontFamily: fonts.bodySemibold, fontSize: 14, color: colors.ink },
});
