import { Link, useLocation } from "react-router-dom";
import { useContext } from "react";
import { AuthContext } from "../../context/auth.context";

import {
  BiLogOut,
  BiListPlus,
  BiListUl,
  BiSolidDiscount,
  BiSolidCategoryAlt
} from "react-icons/bi";

import {
  MdCampaign,
  MdSmartToy
} from "react-icons/md";

import { BsFillPersonFill } from "react-icons/bs";

function Navbar() {
  const {
    isLoggedIn,
    user,
    logOutUser,
    isAdmin
  } = useContext(AuthContext);

  const location = useLocation();

  const isActive = (path) =>
    location.pathname === path;

  const menuItemClass = (path) =>
    `button-menu ${
      isActive(path)
        ? "bg-sidebar-light text-white pl-10"
        : ""
    }`;

  return (
    <nav className="navbar">

      {/* Logo */}
      <div className="px-6 mb-4">
        <Link to="/">
          <img
            src={"./logo.png"}
            width={"180px"}
            className="mx-auto"
            alt="Restauranty"
          />
        </Link>
      </div>

      {/* User */}
      {user ? (
        <div className="px-6 py-3 mx-4 mb-2 bg-sidebar-light rounded-xl">
          <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">
            Welcome back
          </p>

          <p className="text-white font-semibold text-sm">
            {user.name} {user.surname}
          </p>
        </div>
      ) : (
        <div className="px-6 py-3 mx-4 mb-2">
          <p className="text-slate-400 text-sm">
            Welcome to Restauranty
          </p>
        </div>
      )}

      <div className="buttons-main">

        {isLoggedIn && (
          <>

            {/* ========================= */}
            {/* MENU ITEMS */}
            {/* ========================= */}

            {isAdmin && (
              <div className="mb-2">

                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest pl-8 mb-2">
                  Menu Items
                </p>

                <Link to="/items">
                  <button
                    className={menuItemClass("/items")}
                  >
                    <BiListUl className="icons" />
                    Items
                  </button>
                </Link>

                <Link to="/createitem">
                  <button
                    className={menuItemClass(
                      "/createitem"
                    )}
                  >
                    <BiListPlus className="icons" />
                    Create Item
                  </button>
                </Link>

              </div>
            )}

            {/* ========================= */}
            {/* DISCOUNTS */}
            {/* ========================= */}

            {isAdmin && (
              <div className="mb-2">

                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest pl-8 mb-2 mt-4">
                  Discounts
                </p>

                <Link to="/discounts/coupons">
                  <button
                    className={menuItemClass(
                      "/discounts/coupons"
                    )}
                  >
                    <BiSolidDiscount className="icons" />
                    Coupons
                  </button>
                </Link>

                <Link to="/createcoupon">
                  <button
                    className={menuItemClass(
                      "/createcoupon"
                    )}
                  >
                    <BiListPlus className="icons" />
                    Create Coupon
                  </button>
                </Link>

                <Link to="/discounts/campaigns">
                  <button
                    className={menuItemClass(
                      "/discounts/campaigns"
                    )}
                  >
                    <MdCampaign className="icons" />
                    Campaigns
                  </button>
                </Link>

                <Link to="/createcampaign">
                  <button
                    className={menuItemClass(
                      "/createcampaign"
                    )}
                  >
                    <BiListPlus className="icons" />
                    Create Campaign
                  </button>
                </Link>

              </div>
            )}

            {/* ========================= */}
            {/* CATEGORIES */}
            {/* ========================= */}

            {isAdmin && (
              <div className="mb-2">

                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest pl-8 mb-2 mt-4">
                  Categories
                </p>

                <Link to="/dietary">
                  <button
                    className={menuItemClass(
                      "/dietary"
                    )}
                  >
                    <BiSolidCategoryAlt className="icons" />
                    Categories
                  </button>
                </Link>

                <Link to="/createdietary">
                  <button
                    className={menuItemClass(
                      "/createdietary"
                    )}
                  >
                    <BiListPlus className="icons" />
                    Create Category
                  </button>
                </Link>

              </div>
            )}

            {/* ========================= */}
            {/* AI & DEVOPS */}
            {/* ========================= */}

            {isAdmin && (
              <div className="mb-2">

                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest pl-8 mb-2 mt-4">
                  AI & DevOps
                </p>

                <Link to="/assistant">
                  <button
                    className={menuItemClass(
                      "/assistant"
                    )}
                  >
                    <MdSmartToy className="icons" />
                    AI Assistant
                  </button>
                </Link>

              </div>
            )}

            {/* ========================= */}
            {/* PROFILE / LOGOUT */}
            {/* ========================= */}

            <div className="mt-6 pt-4 border-t border-sidebar-light">

              <Link to="/profile">
                <button
                  className={menuItemClass(
                    "/profile"
                  )}
                >
                  <BsFillPersonFill className="icons" />
                  Profile
                </button>
              </Link>

              <button
                onClick={logOutUser}
                className="button-menu text-red-400 hover:text-red-300 hover:bg-red-500/10"
              >
                <BiLogOut className="icons text-red-400" />
                Logout
              </button>

            </div>

          </>
        )}

      </div>

      {/* ========================= */}
      {/* NOT LOGGED IN */}
      {/* ========================= */}

      {!isLoggedIn && (
        <div className="mt-6 px-6 space-y-2">

          <Link to="/login">
            <button className="w-full py-3 bg-primary-600 text-white rounded-xl font-semibold text-sm hover:bg-primary-700 transition-all duration-200 shadow-sm">
              Login
            </button>
          </Link>

          <Link to="/signup">
            <button className="w-full py-3 bg-transparent text-slate-300 border border-slate-500 rounded-xl font-semibold text-sm hover:bg-sidebar-light hover:text-white transition-all duration-200 mt-2">
              Register
            </button>
          </Link>

        </div>
      )}

    </nav>
  );
}

export default Navbar;