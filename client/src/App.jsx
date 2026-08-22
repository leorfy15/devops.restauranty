import "./App.css";
import { Routes, Route } from "react-router-dom";

import HomePage from "./pages/HomePage/HomePage";
import ProfilePage from "./pages/ProfilePage/ProfilePage";
import SignupPage from "./pages/SignupPage/SignupPage";
import LoginPage from "./pages/LoginPage/LoginPage";

import Navbar from "./components/Navbar/Navbar";
import IsPrivate from "./components/IsPrivate/IsPrivate";
import IsAdmin from "./components/IsAdmin/IsAdmin";
import IsAnon from "./components/IsAnon/IsAnon";

import CreateItem from "./pages/Admin/Items/CreateItem/CreateItem";
import EditItem from "./pages/Admin/Items/EditItem/EditItem";
import ItemsPageList from "./pages/Admin/Items/ItemsPageList/ItemsPageList";
import ItemPage from "./pages/Admin/Items/ItemPage/ItemPage";

import CreateCoupon from "./pages/Admin/Coupons/CreateCoupon/CreateCoupon";
import CouponsPageList from "./pages/Admin/Coupons/CouponsPageList/CouponsPageList";
import EditCoupon from "./pages/Admin/Coupons/EditCoupon/EditCoupon";

import CreateDietary from "./pages/Admin/Dietary/CreateDietary/CreateDietary";
import DietaryPageList from "./pages/Admin/Dietary/DietaryPageList/DietaryPageList";
import EditDietary from "./pages/Admin/Dietary/EditDietary/EditDietary";

import CreateCampaign from "./pages/Admin/Campaigns/CreateCampaign/CreateCampaign";
import CampaignsPageList from "./pages/Admin/Campaigns/CampaignsPageList/CampaignsPageList";
import EditCampaign from "./pages/Admin/Campaigns/EditCampaign/EditCampaign";

import AssistantPage from "./pages/Admin/Assistant/AssistantPage";

function App() {
  return (
    <div className="App">
      <div id="main">
        <Navbar />

        <Routes>
          <Route path="/" element={<HomePage />} />

          <Route
            path="/home"
            element={
              <IsPrivate>
                <HomePage />
              </IsPrivate>
            }
          />

          <Route
            path="/profile"
            element={
              <IsPrivate>
                <ProfilePage />
              </IsPrivate>
            }
          />

          <Route
            path="/items"
            element={
              <IsAdmin>
                <ItemsPageList />
              </IsAdmin>
            }
          />

          <Route
            path="/discounts/coupons"
            element={
              <IsAdmin>
                <CouponsPageList />
              </IsAdmin>
            }
          />

          <Route
            path="/items:itemId"
            element={
              <IsAdmin>
                <ItemPage />
              </IsAdmin>
            }
          />

          <Route
            path="/createcoupon"
            element={
              <IsAdmin>
                <CreateCoupon />
              </IsAdmin>
            }
          />

          <Route
            path="/createitem"
            element={
              <IsAdmin>
                <CreateItem />
              </IsAdmin>
            }
          />

          <Route
            path="/createcampaign"
            element={
              <IsAdmin>
                <CreateCampaign />
              </IsAdmin>
            }
          />

          <Route
            path="/discounts/campaigns"
            element={
              <IsAdmin>
                <CampaignsPageList />
              </IsAdmin>
            }
          />

          <Route
            path="/editItem/:itemId"
            element={
              <IsAdmin>
                <EditItem />
              </IsAdmin>
            }
          />

          <Route
            path="/editCoupon/:CouponId"
            element={
              <IsAdmin>
                <EditCoupon />
              </IsAdmin>
            }
          />

          <Route
            path="/EditCampaign/:CampaignId"
            element={
              <IsAdmin>
                <EditCampaign />
              </IsAdmin>
            }
          />

          <Route
            path="/signup"
            element={
              <IsAnon>
                <SignupPage />
              </IsAnon>
            }
          />

          <Route
            path="/login"
            element={
              <IsAnon>
                <LoginPage />
              </IsAnon>
            }
          />

          <Route
            path="/createdietary"
            element={
              <IsAdmin>
                <CreateDietary />
              </IsAdmin>
            }
          />

          <Route
            path="/dietary"
            element={
              <IsAdmin>
                <DietaryPageList />
              </IsAdmin>
            }
          />

          <Route
            path="/editDietary/:DietaryId"
            element={
              <IsAdmin>
                <EditDietary />
              </IsAdmin>
            }
          />

          <Route
            path="/assistant"
            element={
              <IsAdmin>
                <AssistantPage />
              </IsAdmin>
            }
          />
        </Routes>
      </div>
    </div>
  );
}

export default App;