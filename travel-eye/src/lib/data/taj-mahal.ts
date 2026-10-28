import type { Site } from "@/types";

/**
 * Coordinates for the mausoleum are the Wikidata point for Q9141 (precision about 30 metres).
 * The garden, gateway, mosque, and jawab are described from the established layout of the complex.
 * They do not have separate verified coordinates or reference photographs here.
 * Cover photograph: Yann Forget, edited by Jim Carter, “Taj Mahal (Edited).jpeg”, CC BY-SA 4.0, Wikimedia Commons.
 */
const TAJ_CREDIT = {
  author: "Yann Forget, edited by Jim Carter",
  license: "CC BY-SA 4.0",
  source: "Wikimedia Commons",
} as const;

export const TAJ_MAHAL: Site = {
  id: "taj-mahal-agra",
  slug: "taj-mahal",
  name: "Taj Mahal",
  city: "Agra",
  country: "India",
  description:
    "A white marble mausoleum on the bank of the Yamuna at Agra, built for Mumtaz Mahal.",
  overview:
    "The Mughal emperor Shah Jahan commissioned the Taj Mahal after the death of his wife Arjumand Banu Begum, known as Mumtaz Mahal, in 1631. Work on the mausoleum began in 1632. The tomb stands in a charbagh, a garden divided into four parts, with a mosque to the west and a matching hall, the jawab, to the east. UNESCO inscribed the Taj Mahal in 1983.",
  latitude: 27.175,
  longitude: 78.04194444444444,
  coverImage: "/references/taj-mahal.jpg",
  coverAlt: "The Taj Mahal mausoleum in Agra",
  coverCredit: TAJ_CREDIT,
  checkpoints: [
    {
      id: "taj-mahal-mausoleum",
      slug: "mausoleum",
      name: "Mausoleum",
      category: "tomb",
      shortDescription: "The white marble tomb at the centre of the garden.",
      story:
        "The mausoleum is the marble tomb Shah Jahan built for Mumtaz Mahal. It sits on a raised platform, with a large central dome and four minarets at the corners of the terrace. The cenotaphs visitors see are in the main chamber. The graves themselves are in a lower room. This is the only place at the Taj Mahal with a reference photograph the scanner can compare.",
      latitude: 27.175,
      longitude: 78.04194444444444,
      radiusMeters: 80,
      referenceImageUrl: "/references/taj-mahal.jpg",
      referenceImageUrls: ["/references/taj-mahal.jpg"],
      imageCredit: TAJ_CREDIT,
      sortOrder: 1,
    },
    {
      id: "taj-mahal-gateway",
      slug: "darwaza-i-rauza",
      name: "Great Gate",
      category: "gate",
      shortDescription: "The southern gateway that frames the first view of the tomb.",
      story:
        "The main gateway stands at the south end of the garden. It is built of red sandstone with white marble inlay, and the passage through it is the formal approach to the mausoleum. A separate coordinate and a reference photograph for this gateway are not on record, so it can be read here but not matched by the scanner or by location.",
      sortOrder: 2,
    },
    {
      id: "taj-mahal-charbagh",
      slug: "charbagh",
      name: "Charbagh",
      category: "garden",
      shortDescription: "The four-part garden between the gateway and the tomb.",
      story:
        "The garden is a charbagh, divided into four by water channels. The channels meet at a tank on the axis between the great gate and the mausoleum. No surveyed point or reference photograph for the garden is on record, so this place is for reading rather than scanning.",
      sortOrder: 3,
    },
    {
      id: "taj-mahal-mosque",
      slug: "mosque-and-jawab",
      name: "Mosque and jawab",
      category: "mosque",
      shortDescription: "The prayer hall west of the tomb, and the matching hall to the east.",
      story:
        "A mosque stands to the west of the mausoleum, facing the direction of prayer. Opposite it, on the east, the jawab repeats the mosque’s form. The jawab is not a mosque. Neither building has a separate coordinate or reference photograph in this guide.",
      sortOrder: 4,
    },
  ],
};
